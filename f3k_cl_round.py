f3k_task_timing_data = {}

f3k_task_timing_data["f3k_a"] = {
            'name': "F3K Task A - Last 1 x 5:00 in 7:00",
            'description': "F3k Task A - Last flight. Max five minutes. Seven minute working window.",
            'windowTime': 420
}
f3k_task_timing_data["f3k_a2"] = {
            'name': "F3K Task A - Last 1 x 5:00 in 10:00",
            'description': "F3k Task A - Last Flight. Max five minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_b"] = {
            'name': "F3K Task B - Last 2 x 4:00",
            'description': "F3k Task B - Last two flights. Max four minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_b2"] = {
            'name': "F3K Task B - Last 2 x 3:00",
            'description': "F3k Task B - Last two flights. Max three minutes. Seven minute working window.",
            'windowTime': 420
}
f3k_task_timing_data["f3k_c"] = {
            'name': "F3K Task C - All Up 3 x 3:00",
            'description': "F3k Task C - All up last down. Single launch. Max three minutes. Three three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_c2"] = {
            'name': "F3K Task C - All Up 4 x 3:00",
            'description': "F3k Task C - All up last down. Single launch. Max three minutes. Four three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_c3"] = {
            'name': "F3K Task C - All Up 5 x 3:00",
            'description': "F3k Task C - All up last down. Single launch. Max three minutes. Five three minute working windows. Must launch before three second start signal ends.",
            'windowTime': 183
}
f3k_task_timing_data["f3k_d"] = {
            'name': "F3K Task D - Ladder",
            'description': "F3k Task D - Ladder. Increasing time by fifteen seconds. Flights of 30 seconds, 45 seconds, 1 minute, 1 minute 15 seconds, 1 minute 30 seconds, 1 minute 45 seconds, and 2 minutes. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_d2"] = {
            'name': "F3K Task D (2020) - 2 x 5:00",
            'description': "F3k Task D - Two flights only. Max five minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e"] = {
            'name': "F3K Task E - Poker",
            'description': "F3k Task E - Poker. Pilot nominated times. Five max target times. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e2"] = {
            'name': "F3K Task E - Poker (2020) 10",
            'description': "F3k Task E - Poker. Pilot nominated times. Three max target times. Ten minute working window. Must achieve or exceed flight time before proceeding to the next target flight. May call end of window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_e3"] = {
            'name': "F3K Task E - Poker (2020) 15",
            'description': "F3k Task E - Poker. Pilot nominated times. Three max target times. Fifteen minute working window. Must achieve or exceed flight time before proceeding to the next target flight. May call end of window.",
            'windowTime': 900
}
f3k_task_timing_data["f3k_f"] = {
            'name': "F3K Task F - Best 3 x 3:00",
            'description': "F3k Task F - Best three flights. Max three minutes. Maximum six launches. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_g"] = {
            'name': "F3K Task G - Best 5 x 2:00",
            'description': "F3k Task G - Best five flights. Max two minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_h"] = {
            'name': "F3K Task H - 1, 2, 3, 4",
            'description': "F3k Task H - One minute, two minute, three minute and four minute max flights in any order. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_i"] = {
            'name': "F3K Task I - 3 x 3:20",
            'description': "F3k Task I - Three longest flights. Max three minutes twenty seconds. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_j"] = {
            'name': "F3K Task J - Last 3 x 3:00",
            'description': "F3k Task J - Last three flights. Max three minutes. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_k"] = {
            'name': "F3K Task K - Big Ladder",
            'description': "F3k Task K - Big Ladder. Five target flights increasing time by thirty seconds. One minute, one minute thirty seconds, two minutes, two minutes thirty seconds, and three minute flights in order. All time counts. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_l"] = {
            'name': "F3K Task L - Single Flight",
            'description': "F3k Task L - Single flight. Single launch. Max time nine minutes fifty nine seconds. Ten minute working window.",
            'windowTime': 600
}
f3k_task_timing_data["f3k_m"] = {
            'name': "F3K Task M - Huge Ladder 3, 5, 7",
            'description': "F3k Task M - Huge ladder. Three flights only. Three minute, five minute, and seven minnit flights in order. All time achieved counts. Fifteen minute working window.",
            'windowTime': 900
}
f3k_task_timing_data["f3k_n"] = {
            'name': "F3K Task N - Best Flight (9:59 Max)",
            'description': "F3k Task N - Best flight. One flight only. Ten minute working window.",
            'windowTime': 600
}

import logging

#Group class returns iterator/generator for sections (prep, no-fly, work, land, gap)
# pass event.config in so that group can calculate section times
# the group needs to know what round it is part of to get round specific times
# Round class contains list of groups

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

    def sections_iter(self):
        """
        Generator yielding timing sections for this group.
        Each yield is a tuple: (section_name, duration_seconds)
        """
        # Example timings, can be customized via event_config or round/task type
        prep_time = self.event_config.get('prep_time', 10)#300  # seconds
        test_time = self.event_config.get('test_time', 0)  # 45 seconds
        no_fly_time = self.event_config.get('no_fly_time', 6) #60
        work_time = getattr(self.round, 'windowTime', 600)
        land_time = self.event_config.get('land_time', 5) #30
        gap_time = self.event_config.get('gap_time', 2) #2


        ## Add special case for F3K Task C (All Up Last Down)
        

        if prep_time > 0:
            yield ('prep', prep_time)
        if test_time > 0:
            yield ('test', test_time)
        if no_fly_time > 0:
            yield ('no-fly', no_fly_time)
        if work_time > 0:
            yield ('work', work_time)
        if land_time > 0:
            yield ('land', land_time)
        if self.round.short_code.startswith('f3k_c'):
            if no_fly_time > 0:
                yield ('no-fly', no_fly_time)
            if work_time > 0:
                yield ('work', work_time)
            if land_time > 0:
                yield ('land', land_time)            
            if no_fly_time > 0:
                yield ('no-fly', no_fly_time)
            if work_time > 0:
                yield ('work', work_time)
            if land_time > 0:
                yield ('land', land_time)                
        if gap_time > 0:
            yield ('gap', gap_time)

    def __iter__(self):
        return self.sections_iter()

    def __repr__(self):
        return f"Group {self.group_number:2d} of Round {self.round.round_number:2d}"


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
        self.windowTime = f3k_task_timing_data[self.short_code]['windowTime'] /10 
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
                    self.logger.error(f"Pilot {pilot_id} has no data for round {self.round_number}")
                    continue
                assert round_data['round_number'] == self.round_number
                for flight in round_data['flights']:
                    if flight['flight_group'] not in groups:
                        groups[flight['flight_group']] = []
                    groups[flight['flight_group']].append(pilot_id)
        for group_letter in sorted(groups): 
            group_number = letters.index(group_letter)
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