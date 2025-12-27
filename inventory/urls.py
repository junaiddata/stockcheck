from django.urls import path
from . import views

urlpatterns = [

    path('', views.home_redirect, name='home'),

    path('brands/', views.brand_select, name='brand_select'),
    path('search/', views.product_search, name='product_search'),
    path('item/<int:product_id>/', views.product_detail, name='product_detail'),
    path('report/', views.master_report, name='master_report'),

    path('item/popup/<int:product_id>/', views.product_popup, name='product_popup'),
    path('delete/<int:entry_id>/', views.delete_entry, name='delete_entry'),
       path('report/history/<int:product_id>/<int:user_id>/', views.report_detail, name='report_detail'),
]

