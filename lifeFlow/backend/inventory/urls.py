from django.urls import path

from .views import AddInventoryView, ListInventoryView


urlpatterns = [
    path("inventory/add/", AddInventoryView.as_view(), name="inventory_add"),
    path("inventory/", ListInventoryView.as_view(), name="inventory_list"),
]
