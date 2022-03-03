from django.contrib import admin
from django.urls import path
import PriceComparison.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", PriceComparison.views.Home),
    path("getResult", PriceComparison.views.getResult)
]