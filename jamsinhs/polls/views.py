from django.shortcuts import render, redirect
from django.utils import timezone

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist

from .models import Activity, Apply, User, Plan


class IndexView(generic.ListView):
    template_name = 'index.html'
    context_object_name = 'latest_activity_list'

    def get_queryset(self):
        """Return the last five published activitys."""
        current_time = timezone.now()
        return Activity.objects.filter(end_date__gt=current_time).order_by('end_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_time = timezone.now()

        context['plan_list'] = Plan.objects.filter(
            due_date__gt=current_time).order_by('due_date')

        try:
            if self.request.session.has_key("user"):
                user_id = self.request.session['user']
                if user_id == None:
                    context['apply_list'] = []
                    context['user'] = False
                else:
                    user = User.objects.get(pk=user_id)
                    context['apply_list'] = user.get_applylist()
                    context['user'] = user
            else:
                context['apply_list'] = []
                context['user'] = False
        except ObjectDoesNotExist:
            context['apply_list'] = []
            context['user'] = False

        return context


class DetailView(generic.DetailView):
    model = Activity
    template_name = 'detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class ResultsView(generic.DetailView):
    model = Apply
    template_name = 'results.html'


def apply(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    try:
        user_id = request.session['user']
        if user_id == None:
            return redirect('/polls/login/')

        user = User.objects.get(pk=user_id)
    except ObjectDoesNotExist:
        return redirect('/polls/login/')

    applies = activity.apply_set.filter(student_id=user.studentid)
    if len(applies) > 0:
        return render(request, 'detail.html', {
            'activity': activity,
            'error_message': f"{user.studentid} ?????? ?????????????????????",
        })
    current_time = timezone.now()
    if activity.start_date > current_time or activity.end_date < current_time:
        return render(request, 'detail.html', {
            'activity': activity,
            'error_message': f"?????? ??????????????? ????????????. ??????????????? {activity.start_date}?????? {activity.end_date}?????????.",
        })
        # Create New apply
    apply = activity.apply_set.create(student_id=user.studentid,
                                      name=user.name,
                                      reg_date=timezone.now(),
                                      state=1
                                      )

    return HttpResponseRedirect(reverse('polls:results', args=(apply.id,)))


def register(request):
    if request.method == "POST":
        studentid = request.POST['studentid']
        name = request.POST['name']
        password = request.POST['password']
        re_password = request.POST['re_password']
        res_data = {}
        # Check if the request is valid
        if not (studentid and name and password and re_password):
            res_data['error2'] = "?????? ?????? ???????????? ?????????."
        elif not (studentid.isdigit() and (10100 < int(studentid) < 32000)):
            res_data['error2'] = "???????????? ?????? ???????????????."
        elif User.objects.filter(studentid=studentid).exists():
            res_data['error2'] = '?????? ????????? ???????????? ?????? ???????????????.'
        elif password != re_password:
            res_data['error2'] = '??????????????? ????????????.'
        else:
            # Register new user
            user = User(studentid=studentid, name=name,
                        password=make_password(password))
            user.save()
        return render(request, 'login.html', res_data)


def login(request):
    res_data = {}
    if request.method == "GET":
        return render(request, 'login.html')
    elif request.method == "POST":
        login_studentid = request.POST['studentid']
        login_password = request.POST['password']
        if not (login_studentid and login_password):
            res_data['error'] = "???????????? ??????????????? ?????? ???????????? ?????????."
        else:
            try:
                user = User.objects.get(studentid=login_studentid)
                if check_password(login_password, user.password):
                    request.session['user'] = user.id
                    return redirect('/polls/')
                else:
                    res_data['error'] = "??????????????? ???????????????."
            except ObjectDoesNotExist:
                res_data['error'] = "???????????? ?????? ?????? ???????????????"
        return render(request, 'login.html', res_data)


def logout(request):
    request.session.pop('user')
    return redirect('/polls/')
