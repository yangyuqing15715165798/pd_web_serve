from django.urls import path
from .views import delete, route_create, all_routes, pd_data,login

urlpatterns = [
    path("delete", delete),
    path("route_create", route_create),
    path("all_routes", all_routes),
    path("pd_data", pd_data),
    path("login",login)
]
