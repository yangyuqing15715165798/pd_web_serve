from django.shortcuts import render
from .models import pd, dynamic_routes, user_login
from .serializers import RoutesSerializer
import simplejson
import json
import re
from typing import Union, Dict
from .utils import transform_routes_data, res_form

from django.http import JsonResponse, HttpResponse, HttpRequest


def delete(request: HttpRequest):
    try:
        payload = simplejson.loads(request.body)
        id = payload["id"]
        mgr = pd.objects.get(id=id)
        mgr.delete()
        return JsonResponse({"message": "DeleteSuccess"})
    except Exception as e:
        return JsonResponse({"Runstatus": e.args})


def update_by_id(request: HttpRequest):
    try:
        payload = simplejson.loads(request.body)
        id = payload["id"]
        mgr = pd.objects.filter(id=id)
        name = payload["name"]
        cost = payload["cost"]
        deposit = payload["deposit"]
        Statement = payload["Statement"]
        ac = pd()
        ac.id = id
        ac.name = name
        ac.cost = cost
        ac.deposit = deposit
        ac.Statement = Statement
        ac.save()
        return JsonResponse({"message": "UpDateSucess"})
    except Exception as e:
        return JsonResponse({"message": "UpDateError"})


def login(request: Union[HttpRequest, Dict]):
    try:
        user_info = json.loads(request.body)["user_info"]
        username = user_info["username"]
        password = user_info["password"]
        instance = user_login.objects.filter(
            username=username, password=password
        ).exists()
        # print(instance)
        if instance:
            return JsonResponse(res_form(message="登录成功"))
        else:
            return JsonResponse(res_form(30000, message="账号或密码错误"))
    except Exception as e:
        print(e)
        return JsonResponse(res_form(30001, message=e.args))


def pd_data(
    request: Union[HttpRequest, Dict], begin_id=0, data_len=300, waveform_count=1
):
    res_code = 20000
    try:
        # get stream string from font-end,example "/data-stream-1/index"
        if type(request) == dict:
            data_stream = request["route"]
        else:
            data_stream = json.loads(request.body)["route"]

        stream_num = re.search(r"\d+", data_stream).group()
        if not stream_num:
            return JsonResponse(
                res_form(60001, message="please transfer data stream string")
            )

        eligible_count = (
            pd.objects.filter(sample_info_id=stream_num)
            .filter(id__gte=begin_id)
            .count()
        )
        # judging whether the rest count is less than default data_len,if so,set data_len=None
        if eligible_count < data_len:
            data_len = None
            res_code = 50001
        else:
            res_code = 50000

        # search data whose id >= begin_id and length is data_len(if the number of eligible data is less than data_len,then get actual length)~
        all_data = (
            pd.objects.filter(sample_info_id=stream_num, id__gte=begin_id)
            .order_by("id")[:data_len]
            .values_list("id", "max_peak", "phase", "tim", "freq", "waveform")
        )
        id_list, max_peak_list, phase_list, tim_list, freq_list, waveform_list = zip(
            *all_data
        )
        phase_peak_list = list(zip(phase_list, max_peak_list))

        # turn freq and time into scientific counting
        # tim_list = ["{:.2e}".format(num) for num in tim_list]
        # freq_list = ["{:.2e}".format(num) for num in freq_list]

        tim_freq_list = list(zip(tim_list, freq_list))

        # waveform_list = waveform_list[:waveform_count].decode("utf-8")
        # waveform_list = json.loads(waveform_list)
        waveform_list = [
            json.loads(item.decode("utf-8")) for item in waveform_list[:waveform_count]
        ]
        waveform_list = [
            (index, item)
            for sublist in waveform_list
            for index, item in enumerate(sublist)
        ]
        data = {
            "phase_peak": phase_peak_list,
            "tim_freq": tim_freq_list,
            "waveform": waveform_list,
            "last_id": id_list[-1],
        }
        if type(request) == dict:
            return res_form(res_code, data=data)
        else:
            return JsonResponse(res_form(data=data))
    except Exception as e:
        print(e)
        res_code = 60000
        return JsonResponse(res_form(res_code, message="Search failed"))


# def waveform_data(request: Union[HttpRequest, Dict], begin_id=0, data_len=300, waveform_count=1):


def route_create(request: HttpRequest):
    try:
        payload = simplejson.loads(request.body)
        id = payload["id"]
        mgr = dynamic_routes.objects.filter(id=id)
        if mgr:  # 如果数据库中存在
            return JsonResponse({"message": "Exist"})
        else:
            path = payload["path"]
            component = payload["component"]
            children_path = payload["children_path"]
            children_component = payload["children_component"]
            children_name = payload["children_name"]
            children_meta_title = payload["children_meta_title"]
            children_meta_icon = payload["children_meta_icon"]
            ac = dynamic_routes()
            ac.id = id
            ac.path = path
            ac.component = component
            ac.children_path = children_path
            ac.children_component = children_component
            ac.children_name = children_name
            ac.children_meta_title = children_meta_title
            ac.children_meta_icon = children_meta_icon
            ac.save()
            return JsonResponse({"message": "CreateSucess"})

    except Exception as e:
        print(e)
        return JsonResponse({"message": "error"})


def all_routes(request: HttpRequest):
    try:
        # payload = simplejson.loads(request.body)
        routes = dynamic_routes.objects.all()
        serializer = RoutesSerializer(routes, many=True)
        output_data = transform_routes_data(serializer.data)
        data = {"code": 20000, "data": output_data}
        return JsonResponse(data)

    except Exception as e:
        print(e)
        return JsonResponse({"message": "error"})
