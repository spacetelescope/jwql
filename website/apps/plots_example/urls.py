from django.urls import path

from . import views

app_name = 'plots_example'
urlpatterns = [
	path('', views.index, name='index'),
	path('<str:inst>/', views.detail, name='detail'),
]