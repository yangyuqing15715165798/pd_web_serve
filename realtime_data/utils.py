import json
from partial_discharge.views import pd_data

def res_pdData(data):
    res_data = pd_data(request=data,begin_id=data['begin_id'])
    return json.dumps(res_data)