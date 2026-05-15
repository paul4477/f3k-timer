import logging
import time
import audio_library
from task_data import f3k_task_timing_data

SHORT_TIME_DEBUG = False

class Section:
    """
    Represents a section with the running of a group - prep time, test time, no-fly, working, landing etc
    """
    def __init__(self, seconds_length, group_obj, round_obj, section_index, event_config=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_config = event_config or {}
        self.round = round_obj
        self.group = group_obj
        self.updatedWeb = False # only used in announce
        self.betweenWorkingTimes = False
        self.section_index = section_index
        self.sectionTime = seconds_length
        # Dict mapping section-relative slot_time (when to fire) to the value
        # to speak (what to say).  In normal sections these are equal; in
        # CountdownToWorkingMixin sections the spoken value is the
        # countdown-to-working-time equivalent.
        # Default: every 30 seconds + 20 down to 3, key == value.
        self.callout_schedule = {
            t: t for t in
            [x for x in range(seconds_length - 1, 0, -1) if x % 30 == 0]
            + list(range(20, 2, -1))
        }
        # Dict of timestamps for audio callouts
        # All these must be integer second values
        self.audio_times = {}
        self.audio_times[2] = audio_library.effect_countdown_beeps
        self.pre_announce_times = {}
        self.announce_sound = None
        self.announce_sound_generating = False

        #self.audio_times[self.sectionTime - 2] = audio_library.effect_countdown_beeps_end

    def __repr__(self):
        return f"Section {self.get_description()} of Group:{self.group.group_number} of Round:{self.round.round_number} {int(self.sectionTime):3d}secs"
    ## If there are multiple instances of a section class
    ## in a group then lets provide the index - e.g. all up, no-fly, work, landing all can have an index
    def get_flight_number(self):
        try: 
            return list((x for x in self.group.sections if isinstance(x, self.__class__))).index(self) + 1
        except (ValueError, AttributeError):
            return 1
    def get_next_section(self):
        try: return self.group.sections[self.section_index+1]
        except IndexError: 
            self.logger.debug(f"Failed to get_next_section. {self.group.sections}, index: {self.section_index+1}")
            return None
        except AttributeError:
            self.logger.debug(f"Failed to get_next_section. Group: {self.group}")
            return None
    def get_previous_section(self):
        try: return self.group.sections[self.section_index-1]
        except IndexError: return None

    def populate_audio_times(self):
        pass
    def populate_pre_announce_times(self):
        pass    
    def is_no_fly(self):
        # Make the default restrictive so we don't use the base class!
        return True
    def get_serial_code(self):
        return "ST"
    def get_description(self):
        return "Base class, shouldn't see this one."

    def get_time_str(self, slot_time):
        """Return the timer display string for this section (MM:SS).
        Override in subclasses to change what the display shows."""
        return f"{int(slot_time / 60):02d}:{slot_time % 60:02d}"

    def get_time_digits(self, slot_time):
        """Return the timer display digits for this section (MMSS, no colon).
        Override in subclasses to change what scoreboards receive."""
        return f"{int(slot_time / 60):02d}{slot_time % 60:02d}"

    def display_time(self, slot_time):
        """Return the slot_time value to display (e.g. on scoreboard/web).
        Override in subclasses to change what is shown."""
        return slot_time

    def set_audio_time(self, t, sound):
        self.callout_schedule.pop(t, None)
        self.audio_times[t] = sound


class CountdownToWorkingMixin:
    """Mixin for prep/test/no-fly sections in countdown-to-working-time mode.

    Stores a pre-computed offset (sum of the durations of all sections that
    follow this one up to, but not including, WorkingSection) and overrides
    the display helpers so that the big timer and scoreboards show the total
    time remaining until working time begins.

    populate_audio_times() calls super() to let the parent section class
    build its normal callout_schedule (with its own pruning), then walks the
    result and replaces the spoken value for any entry with a trigger time
    above the final-approach threshold: the spoken value becomes
    trigger_time + countdown_offset, i.e. the countdown-to-working value.
    Entries at or below the threshold (15s) are left unchanged so that
    section-relative final-approach callouts ("15", "10"... "3") still fire.

    pre_announce_times on the next section ("30 seconds to working time"
    etc.) are entirely unaffected and continue to take precedence as the
    more descriptive announcement.
    """

    def __init__(self, *args, countdown_offset=0, **kwargs):
        self.countdown_offset = countdown_offset
        super().__init__(*args, **kwargs)

    def get_time_to_working(self, slot_time):
        """Return the total seconds remaining until working time starts."""
        return slot_time + self.countdown_offset

    def display_time(self, slot_time):
        return self.get_time_to_working(slot_time)

    def get_time_str(self, slot_time):
        t = self.get_time_to_working(slot_time)
        return f"{int(t / 60):02d}:{t % 60:02d}"

    def get_time_digits(self, slot_time):
        t = self.get_time_to_working(slot_time)
        return f"{int(t / 60):02d}{t % 60:02d}"

    def populate_audio_times(self):
        
        super().populate_audio_times()  # parent builds its callout_schedule normally
        self.logger.debug(f"populate_audio_times in CountdownToWorkingMixin for {self}. Initial callout_schedule: {self.callout_schedule}")
        FINAL_APPROACH_THRESHOLD = 15
        self.callout_schedule = {
            sv: (sv + self.countdown_offset if sv > FINAL_APPROACH_THRESHOLD else sv)
            for sv, _ in self.callout_schedule.items()
        }
        self.logger.debug(f"populate_audio_times in CountdownToWorkingMixin for {self}. Adjusted callout_schedule: {self.callout_schedule}")

class PrepSection(Section):
    def is_no_fly(self):
        # Note which way round the booleans are here!
        # Config is "be strict", so True means no-fly here
        # This method is "is this a no fly section?"
        return self.event_config.get('use_strict_test_time', False)
    def get_serial_code(self):
        return "PT"
    def get_description(self):
        return "Preparation Time"


    def populate_audio_times(self):
        # Remove callouts that clash with section-start sounds or are
        # covered by pre_announce_times on following sections
        
        self.callout_schedule = {
            t: t for t in
                [15] + list(range(10, 2, -1))
        }

        self.callout_schedule.pop(self.sectionTime - 120, None)

        if isinstance(self.get_next_section(), TestSection):
            self.set_audio_time(2, audio_library.effect_countdown_beeps)
        else:
            self.set_audio_time(2, audio_library.effect_countdown_beeps_end)

        self.set_audio_time(self.sectionTime - 1, audio_library.language_audio['vx_prep_start'])
        self.set_audio_time(self.sectionTime - 5, audio_library.task_audio[self.round.short_code])
        self.set_audio_time(self.sectionTime - 120, self.announcement)

    def announcement(self):
        return self.group.announce_sound
        
class TestSection(Section):
    def is_no_fly(self):
        return False
    def get_serial_code(self):
        return "TT"
    def get_description(self):
        return "Test Flying Time"  
    def populate_audio_times(self):
        for t in [16, 17, 18, 19, 20, 30]:
            self.callout_schedule.pop(t, None)
        self.set_audio_time(2, audio_library.effect_countdown_beeps_end)
        self.set_audio_time(self.sectionTime - 1, audio_library.language_audio['vx_test_time'])
      
    def populate_pre_announce_times(self):
        self.pre_announce_times[-60] = audio_library.language_audio['vx_1m_to_test']
        self.pre_announce_times[-30] = audio_library.language_audio['vx_30s_to_test']
        self.pre_announce_times[-20] = audio_library.language_audio['vx_20s_to_test']

class NoFlySection(Section):
    def is_no_fly(self):
        return True
    def get_serial_code(self):
        return "NF"
    def get_description(self):
        return "No Fly Time"    
    def populate_audio_times(self):
        for t in [18, 19, 20, 30]:
            self.callout_schedule.pop(t, None)
        self.callout_schedule[45] = 45
        self.set_audio_time(self.sectionTime-1, audio_library.language_audio['vx_no_flying'])    

    def populate_pre_announce_times(self):
        if not isinstance(self.get_previous_section(), TestSection): # Test is only 45 seconds
            self.pre_announce_times[-60] = audio_library.language_audio['vx_1m_to_no_fly']
    
        self.pre_announce_times[-30] = audio_library.language_audio['vx_30s_to_no_fly']
        self.pre_announce_times[-20] = audio_library.language_audio['vx_20s_to_no_fly']

        if isinstance(self.group, AllUpGroup):
            ## Ending countdown is actually the start of the round
            ## so we need to use the 3s version for AllUp.
            self.set_audio_time(2, audio_library.effect_countdown_beeps_3s)   

class AllUpNoFlySection(NoFlySection):
    ## Used between the working times
    def populate_pre_announce_times(self):
        ## Alter beep f
        self.set_audio_time(2, audio_library.effect_countdown_beeps_3s)   
        ## Previous section will be landing window
        ## Adjust announcements accordingly
        #self.pre_announce_times.pop(-60)
        #self.pre_announce_times.pop(-30)
        #self.pre_announce_times.pop(-20)
    def get_flight_number(self):
        try: 
            return list((x for x in self.group.sections if (isinstance(x, AllUpNoFlySection) or isinstance(x, NoFlySection)))).index(self) + 1
        except ValueError:
            return 1


class CountdownPrepSection(CountdownToWorkingMixin, PrepSection):
    def populate_audio_times(self):
        
        super().populate_audio_times()  # parent builds its callout_schedule normally
        self.logger.debug(f"populate_audio_times in CountdownPrepSection for {self}. Initial callout_schedule: {self.callout_schedule}")
        FINAL_APPROACH_THRESHOLD = 15
        self.callout_schedule = {
            sv: (sv + self.countdown_offset if sv > FINAL_APPROACH_THRESHOLD else sv)
            for sv, _ in self.callout_schedule.items()
        }
        
        for t in [5*60, 4*60, 3*60]:
            if self.sectionTime + self.countdown_offset > t:
                self.set_audio_time(t - self.countdown_offset, audio_library.language_audio[f'vx_{t//60}m_to_working_time'])
        self.logger.debug(f"populate_audio_times in CountdownPrepSection for {self}. Adjusted callout_schedule: {self.callout_schedule}")
        self.logger.debug(f"populate_audio_times in CountdownPrepSection for {self}. audio_times: {self.audio_times}")

class CountdownTestSection(CountdownToWorkingMixin, TestSection): pass
class CountdownNoFlySection(CountdownToWorkingMixin, NoFlySection): pass


class WorkingSection(Section):
    def is_no_fly(self):
        return False
    def get_serial_code(self):
        return "WT"
    def get_description(self):
        return "Working Time"    
    def populate_audio_times(self):
        for t in [11, 12, 13, 14, 16, 17, 18, 19]:
            self.callout_schedule.pop(t, None)
        match self.sectionTime:
            case 183:
                self.callout_schedule.pop(180, None)
                self.set_audio_time(self.sectionTime-4, audio_library.language_audio['vx_3m_window'])    
            case 420:
                self.set_audio_time(self.sectionTime-1, audio_library.language_audio['vx_7m_window'])    
            case 600:
                self.set_audio_time(self.sectionTime-1, audio_library.language_audio['vx_10m_window'])    
            case 900:
                self.set_audio_time(self.sectionTime-1, audio_library.language_audio['vx_15m_window'])                                                    

    def populate_pre_announce_times(self):
        self.pre_announce_times[-30] = audio_library.language_audio['vx_30s_to_working_time']
        self.pre_announce_times[-20] = audio_library.language_audio['vx_20s_to_working_time']    
    
class LandingSection(Section):
    def is_no_fly(self):
        return True # kind of
    def get_serial_code(self):
        return "LT"
    def get_description(self):
        return "Landing Window"    
    def populate_audio_times(self):
        for t in [11, 12, 13, 14, 16, 17, 18, 19]:
            self.callout_schedule.pop(t, None)
        
        self.set_audio_time(2, audio_library.effect_countdown_beeps_end)
        self.set_audio_time(self.sectionTime-1, audio_library.language_audio['vx_30s_landing_window'])  
        

class GapSection(Section):
    def get_description(self):
        return "Waiting for next group"
    def populate_audio_times(self):
        self.callout_schedule = {}
        self.audio_times = {self.sectionTime-15: audio_library.language_audio['vx_group_sep']}

class AnnounceSection(Section):
    def get_description(self):
        return "Announcement in progress"

    def get_time_str(self, slot_time):
        """Blank the display while the announcement audio is playing."""
        return "--:--"

    def get_time_digits(self, slot_time):
        """Blank the scoreboard while the announcement audio is playing."""
        return "0000"

    def populate_audio_times(self):
        self.callout_schedule = {}
        self.audio_times = {}
        
class ShowTimeSection(GapSection):
    def __repr__(self):
        return f"Section {self.get_description()} "
    def get_serial_code(self):
        return "PT" # DT doesn't work for current Pandora firmware
    def get_description(self):
        return "Actual Time HH:MM"

    def get_time_str(self, slot_time):
        """Display the live wall-clock time (HH:MM) during pre-competition idle."""
        return time.strftime("%H:%M", time.localtime())

    def get_time_digits(self, slot_time):
        """Send the live wall-clock time (HHMM) to scoreboards during pre-competition idle."""
        return time.strftime("%H%M", time.localtime())

    def populate_audio_times(self):
        ## COuld we add the logic here for "Starting in X minutes annoucements?"
        
        self.callout_schedule = {}
        # Reset to clear other values
        self.audio_times = {}


class Group:
    """
    Represents a group within a round. Can generate its timing sections (prep, no-fly, work, land, gap).
    """
    def __init__(self, group_number, group_letter, round_obj, pilot_list, event_config=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.group_number = group_number
        self.group_letter = group_letter
        self.round = round_obj  # Reference to parent Round
        self.pilots = pilot_list  # List of pilot IDs in this group
        self.logger.debug(f"Group got config {event_config}")
        self.event_config = event_config or {}
        # Example: self.sections = list(self.sections_iter())
        
        self.sections = []
        self.populate_sections()
        self.announce_sound = None
        self.announce_sound_generating = False

    def __iter__(self):
        return (section for section in self.sections)
    
    def populate_sections(self):
        prep_time = self.event_config.get('prep_time', 300)
        no_fly_time = self.event_config.get('no_fly_time', 60)
        if self.event_config.get('use_strict_test_time', False):
            test_time = 45
        else:   
            test_time = 0
        work_time = getattr(self.round, 'windowTime', 600)
        land_time = self.event_config.get('land_time', 30)
        group_separation_time = self.event_config.get('group_separation_time', 120)
        countdown_mode = self.event_config.get('countdown_to_working_time', False)

        if countdown_mode:
            actual_prep = prep_time - test_time - no_fly_time
            if actual_prep < 30:
                self.logger.warning(
                    f"countdown_to_working_time: computed prep ({actual_prep}s) is less than minimum "
                    f"30s (prep_time={prep_time}, test={test_time}, no_fly={no_fly_time}). Clamping to 30s."
                )
                actual_prep = 30
        else:
            actual_prep = prep_time

        ## Passing len(self.sections) so that the section knows its own index and we
        ## can use it to reference forward and back.
        self.sections.append(AnnounceSection(999, self, self.round, len(self.sections), self.event_config))
        if actual_prep > 0:
            if countdown_mode:
                self.sections.append(CountdownPrepSection(actual_prep, self, self.round, len(self.sections), self.event_config, countdown_offset=test_time + no_fly_time))
            else:
                self.sections.append(PrepSection(actual_prep, self, self.round, len(self.sections), self.event_config))
        if test_time > 0:
            if countdown_mode:
                self.sections.append(CountdownTestSection(test_time, self, self.round, len(self.sections), self.event_config, countdown_offset=no_fly_time))
            else:
                self.sections.append(TestSection(test_time, self, self.round, len(self.sections), self.event_config))
        if no_fly_time > 0:
            if countdown_mode:
                self.sections.append(CountdownNoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config, countdown_offset=0))
            else:
                self.sections.append(NoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config))
        if work_time > 0:
            self.sections.append(WorkingSection(work_time, self, self.round, len(self.sections), self.event_config))
        if land_time > 0:
            self.sections.append(LandingSection(land_time, self, self.round, len(self.sections), self.event_config))
        if group_separation_time > 0:
            self.sections.append(GapSection(group_separation_time, self, self.round, len(self.sections), self.event_config))
        self.logger.debug(f"{self.sections}")
        
        for section in self.sections:
            section.populate_audio_times()
            section.populate_pre_announce_times()

    def __repr__(self):
        return f"Group {self.group_letter} of Round {self.round.round_number:2d}"

class AllUpGroup(Group):
    def __init__(self, group_number, group_letter, round_obj, pilot_list, event_config=None):
        match round_obj.short_code:
            case "f3k_c":
                self.all_up_flight_count = 3
            case "f3k_c2":
                self.all_up_flight_count = 4
            case "f3k_c3":
                self.all_up_flight_count = 5
            case _:
                self.logger.error(f"Unexpected round short_code in All Up group: {round_obj.short_code}")
        super().__init__(group_number, group_letter, round_obj, pilot_list, event_config=event_config)

    def populate_sections(self):
        prep_time = self.event_config.get('prep_time', 300)
        if self.event_config.get('use_strict_test_time', False):
            test_time = 45
        else:   
            test_time = 0
        no_fly_time = self.event_config.get('no_fly_time', 60)
        work_time = getattr(self.round, 'windowTime', 600)
        land_time = self.event_config.get('land_time', 30)
        group_separation_time = self.event_config.get('group_separation_time', 120)
        countdown_mode = self.event_config.get('countdown_to_working_time', False)

        if countdown_mode:
            actual_prep = prep_time - test_time - no_fly_time
            if actual_prep < 30:
                self.logger.warning(
                    f"countdown_to_working_time: computed prep ({actual_prep}s) is less than minimum "
                    f"30s (prep_time={prep_time}, test={test_time}, no_fly={no_fly_time}). Clamping to 30s."
                )
                actual_prep = 30
        else:
            actual_prep = prep_time

        self.sections.append(AnnounceSection(999, self, self.round, len(self.sections), self.event_config))
        if actual_prep > 0:
            if countdown_mode:
                self.sections.append(CountdownPrepSection(actual_prep, self, self.round, len(self.sections), self.event_config, countdown_offset=test_time + no_fly_time))
            else:
                self.sections.append(PrepSection(actual_prep, self, self.round, len(self.sections), self.event_config))
        if test_time > 0:
            if countdown_mode:
                self.sections.append(CountdownTestSection(test_time, self, self.round, len(self.sections), self.event_config, countdown_offset=no_fly_time))
            else:
                self.sections.append(TestSection(test_time, self, self.round, len(self.sections), self.event_config))
        for i in range(self.all_up_flight_count):
            if no_fly_time > 0:
                if i == 0:
                    if countdown_mode:
                        self.sections.append(CountdownNoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config, countdown_offset=0))
                    else:
                        self.sections.append(NoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config))
                else:
                    self.sections.append(AllUpNoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config))
            if work_time > 0:
                self.sections.append(WorkingSection(work_time, self, self.round, len(self.sections), self.event_config))
            if land_time > 0:
                self.sections.append(LandingSection(land_time, self, self.round, len(self.sections), self.event_config))
        if group_separation_time > 0:
            self.sections.append(GapSection(group_separation_time, self, self.round, len(self.sections), self.event_config))

        for section in self.sections:
            section.populate_audio_times()
            section.populate_pre_announce_times()

# Example usage:
# round_obj = Round('f3k_a', 'A', 1)
# group = Group(1, round_obj, event_config={'prep_time': 60, 'no_fly_time': 30})
# for section, duration in group:
#     print(section, duration)

class Round():
    def __init__(self, short_code, short_name, round_number, event_config=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.short_code = short_code
        self.round_number = round_number
        self.short_name = short_name
        self.event_config = event_config or {}
        self.task_name = f3k_task_timing_data[self.short_code]['name']
        self.task_description = f3k_task_timing_data[self.short_code]['description']
        self.windowTime = f3k_task_timing_data[self.short_code]['windowTime']
        self.group_count = 0

    def __repr__(self):
        return f"Round {self.round_number:2d} {self.short_name}, {int(self.windowTime/60):2d}mins"

    def set_group_data(self, prelim_standings):
        self.standings_data = prelim_standings
        ## Count groups
        
        for pilot in self.standings_data:
            if len(pilot['rounds']) >= 0:
                # Only look at this round
                try: round_data = pilot['rounds'][self.round_number - 1]
                except IndexError:
                    self.logger.warning(f"Pilot {pilot['pilot_id']} has no data for round {self.round_number}")
                    continue

            flight_group = round_data['flights'][0]['flight_group']
            letters= "-ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Adding '-' so index matches group number
            group_number = letters.index(flight_group)
            self.group_count = max(self.group_count, group_number)

    def __iter__(self):
        groups = {}
        letters= "-ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Adding '-' so index matches group number
        #print (self.round_number)
        for pilot in self.standings_data:
            pilot_id = pilot['pilot_id']
            
            # prelim_standings.standings[pilot.rounds[round.flights[flight_group]]]
            if len(pilot['rounds']) >= 0:
                # Only look at this round
                try: round_data = pilot['rounds'][self.round_number - 1]
                except IndexError:
                    self.logger.warning(f"Pilot {pilot_id} has no data for round {self.round_number}")
                    continue

                for flight in round_data['flights']:
                    if flight['flight_group'] not in groups:
                        groups[flight['flight_group']] = []
                    groups[flight['flight_group']].append(pilot_id)
        for group_letter in sorted(groups): 
            group_number = letters.index(group_letter)
            # Make All Up group if this is an All Up round
            if self.short_code.startswith("f3k_c"):
                yield AllUpGroup(group_number, group_letter, self, groups[group_letter], self.event_config) 
            else:
                #self.logger.error(f"Creating standard group {group_letter} with config {self.event_config}")
                yield Group(group_number, group_letter, self, groups[group_letter], self.event_config)

    #def __iter__(self):
    #    return (group for group in self.groups)

def make_rounds(json_data, event_config=None):
  round_data = []
  event_config = event_config or {}
  for round in json_data['event']['tasks']:
    r = Round(
       round['flight_type_code'], 
       round['flight_type_name_short'], 
       round['round_number'],
       event_config=event_config
    )
    r.set_group_data(json_data['event']['prelim_standings']['standings'])
    round_data.append( r )
    ###draw[pilot.pilot_id][task.round_number] = pilot.rounds[parseInt(task.round_number) - 1].flights[0].flight_group
  return round_data   

