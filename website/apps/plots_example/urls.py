from django.urls import path

from . import views

app_name = 'plots_example'
urlpatterns = [
	path('', views.home, name='home'),
	path('<str:inst>/', views.instrument, name='instrument'),
	path('<str:inst>/unlooked/', views.unlooked_images, name='unlooked_im'),
	path('<str:inst>/<str:file>/', views.view_image, name='view_image'),


]