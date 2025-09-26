
from f3k_cl_round import Round

def load_round_data(json_data):
  round_data = []
  for round in json_data['event']['tasks']:
    round_data.append(Round(round['flight_type_code'],round['round_number'],))
  return round_data