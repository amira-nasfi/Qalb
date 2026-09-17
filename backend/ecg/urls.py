from django.urls import path
from . import views

app_name = "ecg"

urlpatterns = [
    # Unified EcgStudy medical loop workflow
    path("studies/", views.upload_and_analyse, name="upload_and_analyse"),
    path("studies/worklist/", views.worklist, name="worklist"),
    path("studies/loop-audit/", views.loop_audit_summary, name="loop_audit_summary"),
    path("studies/<int:pk>/", views.study_detail, name="study_detail"),
    path("studies/<int:pk>/waveform/", views.waveform, name="waveform"),
    path("studies/<int:pk>/transmit/", views.transmit, name="transmit"),
    path("studies/<int:pk>/open/", views.open_study, name="open_study"),
    path("studies/<int:pk>/sign/", views.sign, name="sign"),
    path("studies/<int:pk>/deliver/", views.deliver_to_his, name="deliver"),
    path("studies/<int:pk>/audit/", views.audit, name="audit"),

    # Direct alias for worklist
    path("worklist/", views.worklist, name="direct_worklist"),
]
