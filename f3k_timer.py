import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a talking timer based on data from an F3XVault event."
    )

    parser.add_argument(
        "eventid",
        type=int,
        help="Event ID (integer, required)."
    )

    parser.add_argument(
        "--prep-minutes",
        type=int,
        default=None,
        help="Preparation time in minutes (optional)."
    )

    parser.add_argument(
        "--group-separation-minutes",
        type=int,
        default=None,
        help="Separation time between groups in minutes (optional)."
    )

    return parser.parse_args()


import f3k_cl_round
import f3k_timer_event_loop

if __name__ == "__main__":
    args = parse_args()
    #print(f"Event ID: {args.eventid}")
    #print(f"Prep Minutes: {args.prep_minutes}")
    #print(f"Group Separation Minutes: {args.group_separation_minutes}")
    import json
    data = json.load(open('test_data.json'))
    rounds = f3k_cl_round.make_rounds(data)#print(data['event']['tasks'][0]['flight_type_code'])
    import pprint
    pprint.pprint(rounds)
    for round in rounds:
        f3k_timer_event_loop.run_round(round)