f3k_task_timing_data = {}

f3k_task_timing_data["f3k_a"] = {
            'name': "F3K Task A - Last 1 x 5:00 in 7:00",
            'description': "F3k Task A: Last flight: Max five minutes: Seven minute working window.",
            'windowTime': 420
}
f3k_task_timing_data["f3k_a2"] = {
            'name': "F3K Task A - Last 1 x 5:00 in 10:00",
            'description': "F3k Task A: Last Flight. Max five minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_b"] = {
            'name': "F3K Task B - Last 2 x 4:00",
            'description': "F3k Task B: Last two flights. Max four minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_b2"] = {
            'name': "F3K Task B - Last 2 x 3:00",
            'description': "F3k Task B: Last two flights. Max three minutes. Seven minute working window.",
            'windowTime': 420
}
f3k_task_timing_data["f3k_c"] = {
            'name': "F3K Task C - All Up 3 x 3:00",
            'description': "F3k Task C: All up last down. Single launch. Max three minutes. Three three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_c2"] = {
            'name': "F3K Task C - All Up 4 x 3:00",
            'description': "F3k Task C: All up last down. Single launch. Max three minutes. Four three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_c3"] = {
            'name': "F3K Task C - All Up 5 x 3:00",
            'description': "F3k Task C: All up last down. Single launch. Max three minutes. Five three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_d"] = {
            'name': "F3K Task D - Ladder",
            'description': "F3k Task D: Ladder. Increasing time by fifteen seconds. Flights of 30 seconds, 45 seconds, 1 minute, 1 minute 15 seconds, 1 minute 30 seconds, 1 minute 45 seconds, and 2 minutes. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_d2"] = {
            'name': "F3K Task D (2020) - 2 x 5:00",
            'description': "F3k Task D: Two flights only. Max five minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e"] = {
            'name': "F3K Task E - Poker",
            'description': "F3k Task E: Poker. Pilot nominated times. Five max target times. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e2"] = {
            'name': "F3K Task E - Poker (2020) 10",
            'description': "F3k Task E: Poker. Pilot nominated times. Three max target times. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight. May call end of window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e3"] = {
            'name': "F3K Task E - Poker (2020) 15",
            'description': "F3k Task E: Poker. Pilot nominated times. Three max target times. Fifteen minute working window. Must achieve or exceed flight time before proceeding to the next target flight. May call end of window.",
            'windowTime': 900
}
f3k_task_timing_data["f3k_f"] = {
            'name': "F3K Task F - Best 3 x 3:00",
            'description': "F3k Task F: Best three flights. Max three minutes. Maximum six launches. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_g"] = {
            'name': "F3K Task G - Best 5 x 2:00",
            'description': "F3k Task G: Best five flights. Max two minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_h"] = {
            'name': "F3K Task H - 1, 2, 3, 4",
            'description': "F3k Task H: One minute, two minute, three minute and four minute max flights in any order. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_i"] = {
            'name': "F3K Task I - 3 x 3:20",
            'description': "F3k Task I: Three longest flights. Max three minutes twenty seconds. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_j"] = {
            'name': "F3K Task J - Last 3 x 3:00",
            'description': "F3k Task J: Last three flights. Max three minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_k"] = {
            'name': "F3K Task K - Big Ladder",
            'description': "F3k Task K: Big Ladder. Five target flights increasing time by thirty seconds. One minute, one minute thirty seconds, two minutes, two minutes thirty seconds, and three minute flights in order. All time counts. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_l"] = {
            'name': "F3K Task L - Single Flight",
            'description': "F3k Task L: Single flight. Single launch. Max time nine minutes fifty nine seconds. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_m"] = {
            'name': "F3K Task M - Huge Ladder 3, 5, 7",
            'description': "F3k Task M: Huge ladder. Three flights only. Three minute, five minute, and seven minnit flights in order. All time achieved counts. Fifteen minute working window.",
            'windowTime': 900
}
f3k_task_timing_data["f3k_n"] = {
            'name': "F3K Task N - Best Flight (9:59 Max)",
            'description': "F3k Task N: Best flight. One flight only. Ten minute working window.",
            'windowTime': 600
}

import logging

#Group class returns iterator/generator for sections (prep, no-fly, work, land, gap)
# pass event.config in so that group can calculate section times
# the group needs to know what round it is part of to get round specific times
# Round class contains list of groups

SHORT_TIME_DEBUG = False
import audio_library
class Section:
    """
    Represents a section with the running of a group - prep time, test time, no-fly, working, landing etc
    """
    def __init__(self, seconds_length, group_obj, round_obj, section_index, event_config=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.event_config = event_config or {}
        self.round = round_obj
        self.group = group_obj
        self.section_index = section_index
        self.sectionTime = seconds_length
        # List of times that will trigger audio calls
        # Default is every 30 seconds + 20 down to 5.
        # Excluding the first second which will usually be covered by the pre-section
        # announcement or the start of section announcement
        self.say_seconds = list((x for x in range(seconds_length-1, 0 ,-1) if x%30==0)) + list(range(20,4,-1))
        # Dict of timestamps for audio callouts
        # All these must be integer second values
        self.audio_times = {}
        self.audio_times[4] = audio_library.effect_countdown_beeps
        self.populate_audio_times()
        self.pre_announce_times = {}
        self.populate_pre_announce_times()
        
        #self.audio_times[self.sectionTime - 2] = audio_library.effect_countdown_beeps_end

    def __repr__(self):
        return f"Section {self.get_description()} of {self.group} of {self.round} {int(self.sectionTime):3d}secs"
    
    def get_next_section(self):
        try: return self.group.sections[self.section_index+1]
        except IndexError: 
            self.logger.debug(f"Failed to get_next_section. {self.group.sections}, index: {self.section_index+1}")
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

class PrepSection(Section):
    def is_no_fly(self):
        # Note which way round the booleans are here!
        # Config is CAN fly in prep.
        # This method is "is this a no fly section?"
        return not self.event_config.get('can_fly_in_prep', True)
    def get_serial_code(self):
        return "PT"
    def get_description(self):
        return "Preparation Time"
    def populate_audio_times(self):
        try:
            self.say_seconds.remove(19)
            self.say_seconds.remove(20)
            self.say_seconds.remove(30) # for no-fly anouncements (or test announcements)
            self.say_seconds.remove(60)
            if isinstance(self.get_next_section(), TestSection):
                self.audio_times[4] = audio_library.effect_countdown_beeps
            else:
                self.audio_times[4] = audio_library.effect_countdown_beeps_end
               
        except IndexError:
            pass
        self.audio_times[self.sectionTime - 1] = audio_library.language_audio['vx_prep_start']
        self.audio_times[self.sectionTime - 3] = audio_library.task_audio[self.round.short_code]
        
class TestSection(Section):
    def is_no_fly(self):
        return False
    def get_serial_code(self):
        return "TT"
    def get_description(self):
        return "Test Flying Time"  
    def populate_audio_times(self):

        self.say_seconds.remove(19)
        self.say_seconds.remove(20)
        self.say_seconds.remove(30) # for no-fly anouncements (or test announcements)
        self.audio_times[4] = audio_library.effect_countdown_beeps_end
        self.audio_times[self.sectionTime-1] = audio_library.language_audio['vx_test_time']
      
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

        self.say_seconds.remove(19)
        self.say_seconds.remove(20)
        self.say_seconds.remove(30)
               
        self.audio_times[self.sectionTime-1] = audio_library.language_audio['vx_no_flying']    

    def populate_pre_announce_times(self):
        if not isinstance(self.get_previous_section(), TestSection): # Test is only 45 seconds
            self.pre_announce_times[-60] = audio_library.language_audio['vx_1m_to_no_fly']
    
        if isinstance(self.group, AllUpGroup):
            ## Ending countdown is actually the start of the round
            ## so we need to use the 3s version for AllUp.
            self.audio_times[4] = audio_library.effect_countdown_beeps_3s   
        else:
            self.pre_announce_times[-30] = audio_library.language_audio['vx_30s_to_no_fly']
            self.pre_announce_times[-20] = audio_library.language_audio['vx_20s_to_no_fly']

class WorkingSection(Section):
    def is_no_fly(self):
        return False
    def get_serial_code(self):
        return "WT"
    def get_description(self):
        return "Working Time"    
    def populate_audio_times(self):
        self.say_seconds.remove(19)
        self.say_seconds.remove(18)
        self.say_seconds.remove(17)
        self.say_seconds.remove(16)
        self.say_seconds.remove(14)
        self.say_seconds.remove(13)
        self.say_seconds.remove(12)
        self.say_seconds.remove(11)
        match self.sectionTime:
            case 183:
                self.say_seconds.remove(180)
                self.audio_times[self.sectionTime-4] = audio_library.language_audio['vx_3m_window']    
            case 420:
                self.audio_times[self.sectionTime-1] = audio_library.language_audio['vx_7m_window']    
            case 600:
                self.audio_times[self.sectionTime-1] = audio_library.language_audio['vx_10m_window']    
            case 900:
                self.audio_times[self.sectionTime-1] = audio_library.language_audio['vx_15m_window']                                                    

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
        self.say_seconds.remove(19)
        self.say_seconds.remove(18)
        self.say_seconds.remove(17)
        self.say_seconds.remove(16)
        self.say_seconds.remove(14)
        self.say_seconds.remove(13)
        self.say_seconds.remove(12)
        self.say_seconds.remove(11)
        #self.say_seconds.remove(20)
        #self.say_seconds.remove(30)
        #self.say_seconds.remove(60)

        self.audio_times[4] = audio_library.effect_countdown_beeps_end
        self.audio_times[self.sectionTime-2] = audio_library.language_audio['vx_30s_landing_window']  
        

class GapSection(Section):
    def get_description(self):
        return "Waiting for next group"
    def populate_audio_times(self):
        self.say_seconds = []
        # Reset to clear other values
        self.audio_times = {self.sectionTime-15: audio_library.language_audio['vx_round_sep']}

class AnnounceSection(GapSection):
    def get_description(self):
        return "Announcement in progress"
    
class ShowTimeSection(GapSection):
    def get_serial_code(self):
        return "DT"
    def get_description(self):
        return "Actual Time HH:MM"
    
class Group:
    """
    Represents a group within a round. Can generate its timing sections (prep, no-fly, work, land, gap).
    """
    def __init__(self, group_number, round_obj, pilot_list, event_config=None):
        self.group_number = group_number
        self.round = round_obj  # Reference to parent Round
        self.pilots = pilot_list  # List of pilot IDs in this group
        self.event_config = event_config or {}
        # Example: self.sections = list(self.sections_iter())
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sections = []
        self.populate_sections()

    def __iter__(self):
        return (section for section in self.sections)
    
    def populate_sections(self):
        # Example timings, can be customized via event_config or round/task type
        if SHORT_TIME_DEBUG:
            prep_time = self.event_config.get('prep_time', 10)
            test_time = self.event_config.get('test_time', 5)
            no_fly_time = self.event_config.get('no_fly_time', 6)
            work_time = getattr(self.round, 'windowTime', 600)
            land_time = self.event_config.get('land_time', 5)
            gap_time = self.event_config.get('gap_time', 2)
        else:
            prep_time = self.event_config.get('prep_time', 300)
            test_time = self.event_config.get('test_time', 0)
            no_fly_time = self.event_config.get('no_fly_time', 60)
            work_time = getattr(self.round, 'windowTime', 600)
            land_time = self.event_config.get('land_time', 30)
            gap_time = self.event_config.get('gap_time', 120)

        ## Passing len(self.sections) so that the section knows its own index and we
        ## can use it to reference forward and back.
        if prep_time > 0:
            self.sections.append(PrepSection(prep_time, self, self.round, len(self.sections), self.event_config))
        if test_time > 0:
            self.sections.append(TestSection(test_time, self, self.round, len(self.sections), self.event_config))
        if no_fly_time > 0:
            self.sections.append(NoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config))
        if work_time > 0:
            self.sections.append(WorkingSection(work_time, self, self.round, len(self.sections), self.event_config))
        if land_time > 0:
            self.sections.append(LandingSection(land_time, self, self.round, len(self.sections), self.event_config))
        if gap_time > 0:
            self.sections.append(GapSection(gap_time, self, self.round, len(self.sections), self.event_config))
        self.logger.error(f"{self.sections}")
    def __repr__(self):
        return f"Group {self.group_number:2d} of Round {self.round.round_number:2d}"

class AllUpGroup(Group):
    def __init__(self, group_number, round_obj, pilot_list, event_config=None):
        match round_obj.short_code:
            case "f3k_c":
                self.all_up_flight_count = 3
            case "f3k_c2":
                self.all_up_flight_count = 3
            case "f3k_c3":
                self.all_up_flight_count = 3
            case _:
                self.logger.error(f"Unexpected round short_code in All Up group: {round_obj.short_code}")
        super().__init__(group_number, round_obj, pilot_list, event_config=None)

    def populate_sections(self):
        # Example timings, can be customized via event_config or round/task type
        if SHORT_TIME_DEBUG:
            prep_time = self.event_config.get('prep_time', 10)
            test_time = self.event_config.get('test_time', 5)
            no_fly_time = self.event_config.get('no_fly_time', 6)
            work_time = getattr(self.round, 'windowTime', 15)
            land_time = self.event_config.get('land_time', 5)
            gap_time = self.event_config.get('gap_time', 2)
        else:
            prep_time = self.event_config.get('prep_time', 300)
            test_time = self.event_config.get('test_time', 0)
            no_fly_time = self.event_config.get('no_fly_time', 60)
            work_time = getattr(self.round, 'windowTime', 600)
            land_time = self.event_config.get('land_time', 30)
            gap_time = self.event_config.get('gap_time', 120)

        if prep_time > 0:
            self.sections.append(PrepSection(prep_time, self, self.round, len(self.sections), self.event_config))
        if test_time > 0:
            self.sections.append(TestSection(test_time, self, self.round, len(self.sections), self.event_config))
        for i in range(self.all_up_flight_count):
            if no_fly_time > 0:
                self.sections.append(NoFlySection(no_fly_time, self, self.round, len(self.sections), self.event_config))
            if work_time > 0:
                self.sections.append(WorkingSection(work_time, self, self.round, len(self.sections), self.event_config))
            if land_time > 0:
                self.sections.append(LandingSection(land_time, self, self.round, len(self.sections), self.event_config))
        if gap_time > 0:
            self.sections.append(GapSection(gap_time, self, self.round, len(self.sections), self.event_config))

# Example usage:
# round_obj = Round('f3k_a', 'A', 1)
# group = Group(1, round_obj, event_config={'prep_time': 60, 'no_fly_time': 30})
# for section, duration in group:
#     print(section, duration)

class Round():
    def __init__(self, short_code, short_name, round_number):
        self.short_code = short_code
        self.round_number = round_number
        self.short_name = short_name
        self.task_name = f3k_task_timing_data[self.short_code]['name']
        self.task_description = f3k_task_timing_data[self.short_code]['description']
        self.windowTime = f3k_task_timing_data[self.short_code]['windowTime']
        self.groups = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def __repr__(self):
        return f"Round {self.round_number:2d} {self.short_name}, {int(self.windowTime/60):2d}mins"

    def populate_groups(self, standings):
        groups = {}
        letters= "-ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Adding '-' so index matches group number
        #print (self.round_number)
        for pilot in standings:
            pilot_id = pilot['pilot_id']
            
            # prelim_standings.standings[pilot.rounds[round.flights[flight_group]]]
            if len(pilot['rounds']) >= 0:
                # Only look at this round
                try: round_data = pilot['rounds'][self.round_number - 1]
                except IndexError:
                    self.logger.warning(f"Pilot {pilot_id} has no data for round {self.round_number}")
                    continue
                assert round_data['round_number'] == self.round_number
                for flight in round_data['flights']:
                    if flight['flight_group'] not in groups:
                        groups[flight['flight_group']] = []
                    groups[flight['flight_group']].append(pilot_id)
        for group_letter in sorted(groups): 
            group_number = letters.index(group_letter)
            # Make All Up group if this is an All Up round
            if self.short_code.startswith("f3k_c"):
                self.groups.append( AllUpGroup(group_number, self, groups[group_letter]) )
            else:
                self.groups.append( Group(group_number, self, groups[group_letter]) )

    def __iter__(self):
        return (group for group in self.groups)

def make_rounds(json_data):
  round_data = []
  for round in json_data['event']['tasks']:
    r = Round(
       round['flight_type_code'], 
       round['flight_type_name_short'], 
       round['round_number'],)
    r.populate_groups(json_data['event']['prelim_standings']['standings'])
    round_data.append( r )
    ###draw[pilot.pilot_id][task.round_number] = pilot.rounds[parseInt(task.round_number) - 1].flights[0].flight_group
  return round_data   

