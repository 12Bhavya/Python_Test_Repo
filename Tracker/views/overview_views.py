from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse,Http404,HttpResponseRedirect
from django.contrib.auth.models import User, Group
from Tracker.models import project,sprint,task,tag
from django.contrib.auth import authenticate, login, logout
#from datetime import datetime, timezone, timedelta
from datetime import datetime, timedelta
from django.utils import timezone 
from dateutil.rrule import rrule, MONTHLY, DAILY, YEARLY
from Tracker.forms import NewProject
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from calendar import HTMLCalendar
from datetime import date
from itertools import groupby
from django.utils.html import conditional_escape as esc
from django.db.models import Q
from django.contrib.auth.decorators import login_required

#............Login...............

def log(request):
    context = {
    }
    return render(request,'Tracker/login.html',context)

def login_next(request):
    name = request.POST.get('name', None)
    pwd = request.POST.get('pwd', None)
    user = authenticate(username=name, password=pwd)
    if user is not None:
        login(request, user)
        g = user.groups.all()[0]
        is_member = Q(assign = user)
        is_open = Q(state = "open")
        is_blocked = Q(state = "blocked")
        all_tasks = task.objects.filter(is_member)
        t = task.objects.filter(is_member & (is_blocked | is_open))
        t_count = task.objects.filter(is_member & (is_blocked | is_open)).count()
        context ={
            'group': g,
            'user': user,
            'task':t,
            'all_tasks':all_tasks,
            't_count':t_count
        }
        return render(request,'Tracker/home.html',context)
    else:
        return HttpResponseRedirect('/Tracker/')

def log_end(request):
    logout(request)
    return HttpResponseRedirect('/Tracker/')

def signup(request):
    if request.method == 'POST':
        username= request.POST.get('username', None)
        pwd = request.POST.get('password', None)
        email = request.POST.get('email', None)
        user = User.objects.create_user(username, email, pwd)
        user.last_name = request.POST.get('lname', None)
        user.first_name = request.POST.get('fname', None)
        user.save()
        group_name = request.POST.get('group',None)
        g = Group.objects.get(name=group_name) 
        g.user_set.add(user)
        return HttpResponseRedirect('/Tracker/')
    else:
        l = Group.objects.all()
        context = {
            'groups':l,
        }
        return render(request, 'Tracker/signup.html',context)

def add_group(request):
    if request.method == 'POST':
        group_name = request.POST.get('group',None)
        g = Group.objects.create(name=group_name)
        g.save()
        return HttpResponseRedirect('/Tracker/signup')
    else:
        context = {
        }
        return render(request, 'Tracker/add_group.html',context)


def home(request):
    user = User.objects.get(username=request.user.username)
    g = user.groups.all()[0]
    is_member = Q(assign = user)
    is_open = Q(state = "open")
    is_blocked = Q(state = "blocked")
    all_tasks = task.objects.filter(is_member)
    t = task.objects.filter(is_member & (is_blocked | is_open))
    t_count = task.objects.filter(is_member & (is_blocked | is_open)).count()
    nt_task = task.objects.filter(is_member)
    today = datetime.today()
    now = datetime.now()
    near_deadline = []
    over_due = []
    new_task = []
    
    nd_count = 0
    nt_count = 0
    od_count = 0
    
    for t1 in t:
        if ((t1.due_date - datetime.date(today) ).days <= 2 ):
            if (((t1.due_date - datetime.date(today) ).days >= 0 ) ):
                near_deadline.append(t1)
                nd_count = nd_count+1
            else:
                over_due.append(t1)
                od_count = od_count+1
            
    for t2 in nt_task:
        if(( datetime.date(today) - datetime.date(t2.created) ).days <= 2 ):
            new_task.append(t2)
            nt_count = nt_count+1
            
    noti = nd_count + nt_count + od_count
    context ={
        'group': g,
        'user': user,
        'task':t,
        'all_tasks':all_tasks,
        't_count':t_count, 
        'near_deadline':near_deadline, 
        'nd_count':nd_count, 
        'new_task':new_task, 
        'nt_count':nt_count, 
        'od_count':od_count, 
        'over_due':over_due, 
        'noti':noti
    }
    return render(request,'Tracker/home.html',context)

#.........Project Views..................

@login_required
def add_project(request):
    if request.method == 'POST':
        form = NewProject(request.POST)
        if form.is_valid():
            new_project = form.save()
            return HttpResponseRedirect('/Tracker/home')
    else:
        user = User.objects.get(username=request.user.username)
        g = request.user.groups.all()[0]
        form = NewProject(initial={'pgroup': g})
        return render(request, 'Tracker/add_project.html', {'form': form,'user':user})

@login_required
def edit_project(request,project_id):
    user = User.objects.get(username=request.user.username)
    if request.method == 'POST':
        p = get_object_or_404(project,pk=project_id)
        form = NewProject(request.POST,instance=p)
        if form.is_valid():
            form.save()
    else:
        p = get_object_or_404(project,pk=project_id)
        form = NewProject(instance=p)

    completed_tp = 0
    total_tp = 0
    t = task.objects.filter(tproject = project_id)
    for tk in t:
        if tk.state == 'completed':
            completed_tp = completed_tp + tk.tp
        total_tp = total_tp + tk.tp
    today = datetime.today()
    tdays = (p.pdeadline - p.pcreated).days
    pdays = (datetime.date(today) - datetime.date(p.pcreated)).days
    ideal_tp = total_tp/tdays*pdays
    real_tp = completed_tp
    if ideal_tp <= real_tp:
        ps = 'Green'
    elif ideal_tp <= real_tp+ideal_tp*0.3 :
        ps = 'Yellow'
    else:
        ps = 'Red'
    context ={
        'project': p,
        'form': form,
        'ps': ps,
        'user':user,
      }
    return render(request, 'Tracker/edit_project.html', context)


@login_required
def delete_project(request,project_id):
    p = get_object_or_404(project,pk=project_id)
    project.objects.filter(id=project_id).delete()
    return HttpResponseRedirect('/Tracker/home/')


@login_required
def search_tag(request):
    tag_name = request.POST.get('textfield', None)
    try:
        user = tag.objects.get(tag = tag_name)
        html = ("<h1>Tasks Associated With Tag</h1>", user.task)
        return HttpResponse(html)
    except tag.DoesNotExist:
        return HttpResponse("There is no task associated with this tag")  


@login_required
def pieview(request,project_id):
    open_tasks = 0
    complete_tasks = 0
    blocked_tasks = 0
    open_tp = 0
    complete_tp = 0
    blocked_tp = 0
    errorchart = 0
    p = get_object_or_404(project,pk=project_id)
    q = task.objects.filter(tproject = project_id)
    days = 0
    months = []
    dates = []
    years = []
    categories = []
    idealdata = []
    
    for e in q:
        if e.state == 'open':
            open_tasks = open_tasks + 1
            open_tp = open_tp + e.tp
        elif e.state == 'completed':
            complete_tasks = complete_tasks + 1
            complete_tp = complete_tp + e.tp
        elif e.state == 'blocked':
            blocked_tasks = blocked_tasks + 1
            blocked_tp = blocked_tp + e.tp
            
    total_tasks = open_tasks + complete_tasks + blocked_tasks
    total_tp = open_tp + complete_tp + blocked_tp
    realdata = []

    now = datetime.now(timezone.utc)
    days = (p.pdeadline - p.pcreated).days
    if (total_tasks > 0):
        if (p.pcreated<=p.pdeadline):
            months = [dt for dt in rrule(MONTHLY, dtstart=p.pcreated, until=p.pdeadline)]
            dates = [dt for dt in rrule(DAILY, dtstart=p.pcreated, until=p.pdeadline)]
            years = months = [dt for dt in rrule(YEARLY, dtstart=p.pcreated, until=p.pdeadline)]
            errorchart = 0
        else:

            errorchart = 1

        for i in range(days+1):
            x = sum(e.tp for e in q if datetime.date(e.created) <= (datetime.date(p.pcreated) + timedelta(days=i)))
            y = sum(e.tp for e in q if (e.comp_time!=None) and (datetime.date(e.comp_time) <= (datetime.date(p.pcreated) + timedelta(days=i))))
            realdata.append(x-y)
            categories = [str(dt.day) + ' ' + dt.strftime("%b") for dt in dates]
            diff = int(round(total_tp/(days+1)))
            idealdata = [total_tp - (i*diff) for i in range(days+1)]

        
    
    '''elif days >= 365:
        categories = [dt.strftime("%b") + " '" + dt.strftime("%y") for dt in months]
    elif days > 730:
        categories = [str(dt.year) for dt in years]'''
        
    context = { 'complete_tasks': complete_tasks, 
        'blocked_tasks': blocked_tasks, 
        'open_tasks': open_tasks,
        'days' : days,
        'months': months,
        'dates' : dates,
        'categories' : categories,
        'idealdata' : idealdata,
        'realdata': realdata,
        'errorchart': errorchart
    }
    if total_tasks>0:
        return render(request, 'Tracker/charts.html', context)
    else:
        return render(request, 'Tracker/nochart.html', context)


@login_required
class Calendar(HTMLCalendar):

    def __init__(self, my_tasks):
        super(Calendar, self).__init__()
        self.my_tasks = self.group_by_day(my_tasks)

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if date.today() == date(self.year, self.month, day):
                cssclass += ' today'
            if day in self.my_tasks:
                cssclass += ' filled'
                body = ['<ul class="sample">']
                for workout in self.my_tasks[day]:
                    body.append('<li>')
                    #body.append('<a href="%s">' % workout.get_absolute_url())
                    #body.append('<a href="Tracker/calendar1/">')
                    body.append(esc(workout.tname))
                    body.append('</a></li>')
                    #body.append('</li>')
                body.append('</ul>')
                return self.day_cell(cssclass, '%d %s' % (day, ''.join(body)))
            return self.day_cell(cssclass, day)
        return self.day_cell('noday', '&nbsp;')
    
    def formatmonth(self, year, month):
        self.year, self.month = year, month
        return super(Calendar, self).formatmonth(year, month)

    def group_by_day(self,my_tasks):
        field = lambda workout: workout.due_date.day
        return dict(
            [(day, list(items)) for day, items in groupby(my_tasks, field)]
        )

    def day_cell(self, cssclass, body):
        return '<td class="%s">%s</td>' % (cssclass, body)


@login_required
def calendar(request,project_id):
    try:
        user = User.objects.get(username=request.user.username)
        q = task.objects.filter(tproject = project_id)
        t = q.latest('due_date')
        year=t.due_date.year
        month=t.due_date.month
        my_tasks = q.order_by('due_date').filter(due_date__year=year, due_date__month=month)
        cal = Calendar(my_tasks).formatmonth(year,month)
        #return render_to_response('Tracker/calendar.html', {'calendar':(cal),})
        return render_to_response('Tracker/calendar.html', {'calendar': mark_safe(cal),'project_id':project_id,'user':user,'year':year,'month':month})
    except task.DoesNotExist:
        return HttpResponse("There is no task associated with this project")  


@login_required        
def calendar1(request,project_id,year,month):
    year=int(year)
    month=int(month)
    if month<2: 
        month=12
        year=year-1
    else:
        month=month-1
    q = task.objects.filter(tproject = project_id)
    user = User.objects.get(username=request.user.username)
    my_tasks = q.order_by('due_date').filter(due_date__year=year, due_date__month=month)
    cal = Calendar(my_tasks).formatmonth(year,month)
    return render_to_response('Tracker/calendar.html', {'calendar': mark_safe(cal),'project_id':project_id,'user':user,'year':year,'month':month})


@login_required
def calendar2(request,project_id,year,month):
    year=int(year)
    month=int(month)
    if month>11:    
        month=1
        year=year+1
    else:
        month=month+1
    user = User.objects.get(username=request.user.username)
    q = task.objects.filter(tproject = project_id)
    my_tasks = q.order_by('due_date').filter(due_date__year=year, due_date__month=month)
    cal = Calendar(my_tasks).formatmonth(year,month)
    return render_to_response('Tracker/calendar.html', {'calendar': mark_safe(cal),'project_id':project_id,'user':user,'year':year,'month':month})
