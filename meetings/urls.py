from django.urls import path

from . import views

urlpatterns = [
    path("", views.exhibition_list, name="exhibition_list"),
    path("language/<str:lang>/", views.set_language, name="set_language"),
    path("new/", views.exhibition_edit, name="exhibition_create"),
    path("<int:pk>/", views.exhibition_detail, name="exhibition_detail"),
    path("<int:pk>/settings/", views.exhibition_edit, name="exhibition_edit"),
    path("<int:pk>/upload/<str:what>/", views.upload, name="upload"),
    path("<int:pk>/template/<str:what>/", views.template_file, name="template_file"),
    path("<int:pk>/run/", views.run, name="run"),
    path("<int:pk>/lock/", views.toggle_lock, name="toggle_lock"),
    path("<int:pk>/timetable/", views.timetable, name="timetable"),
    path("<int:pk>/meetings/add/", views.meeting_add, name="meeting_add"),
    path("<int:pk>/meetings/<int:meeting_id>/move/", views.meeting_move, name="meeting_move"),
    path("<int:pk>/meetings/<int:meeting_id>/delete/", views.meeting_delete, name="meeting_delete"),
    path("<int:pk>/export/excel/", views.export_excel, name="export_excel"),
    path("<int:pk>/export/pdf/<str:kind>/", views.export_pdf, name="export_pdf"),
]
