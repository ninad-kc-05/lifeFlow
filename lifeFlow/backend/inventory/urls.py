from django.urls import path

from .views import AddInventoryView, ListInventoryView, InventorySummaryView


urlpatterns = [
    path("inventory/add/", AddInventoryView.as_view(), name="inventory_add"),
    path("inventory/summary/", InventorySummaryView.as_view(), name="inventory_summary"),
    path("inventory/", ListInventoryView.as_view(), name="inventory_list"),
]
