
from f3k_cl_competition import Round, Group, make_rounds


if __name__ == "__main__":
  import json
  data = json.load(open('test_data.json'))
  rounds = make_rounds(data)
  for round in rounds:
    print(round)
    grp_iter = (group for group in round                )
    print(next(grp_iter))
    print(next(grp_iter))

    #for group in round:
    #  print(f" Group {group.group_number} pilots: {group.pilots}")
    #  print(next((s for s in group)))