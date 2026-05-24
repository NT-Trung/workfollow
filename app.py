from datetime import date, datetime, timedelta
from calendar import monthrange
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = os.getenv('DB_PORT')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

STATUSES = ['Chưa bắt đầu', 'Đang làm', 'Hoàn thành', 'Tạm hoãn']
PRIORITIES = ['Cao', 'Trung bình', 'Thấp']
GROUPS = ['Công việc', 'Website Redesign', 'Marketing', 'Họp hành', 'Cá nhân', 'Nghiên cứu']

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default='')
    start_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(30), nullable=False, default='Trung bình')
    status = db.Column(db.String(30), nullable=False, default='Chưa bắt đầu')
    group_name = db.Column(db.String(100), nullable=False, default='Công việc')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_overdue(self):
        return self.due_date < date.today() and self.status != 'Hoàn thành'


def parse_date(value, fallback=None):
    if not value:
        return fallback or date.today()
    return datetime.strptime(value, '%Y-%m-%d').date()


def ensure_seed_data():
    db.create_all()
    if Task.query.count() > 0:
        return
    today = date.today()
    samples = [
        ('Hoàn thiện báo cáo dự án', 'Tổng hợp tiến độ và gửi quản lý', 0, 1, 'Cao', 'Đang làm', 'Công việc', 'Ưu tiên hoàn thành trong hôm nay'),
        ('Thiết kế giao diện trang chủ', 'Hoàn thiện dashboard responsive', -2, 3, 'Trung bình', 'Đang làm', 'Website Redesign', ''),
        ('Họp nhóm định kỳ', 'Review sprint và phân công việc', 1, 4, 'Thấp', 'Chưa bắt đầu', 'Họp hành', ''),
        ('Viết nội dung landing page', 'Soạn nội dung trang giới thiệu', -1, 5, 'Trung bình', 'Chưa bắt đầu', 'Marketing', ''),
        ('Viết tài liệu hướng dẫn', 'Tài liệu sử dụng WorkFollow', -6, -1, 'Cao', 'Hoàn thành', 'Công việc', ''),
        ('Nghiên cứu từ khóa SEO', 'Tìm bộ từ khóa cho chiến dịch mới', -4, 2, 'Trung bình', 'Hoàn thành', 'Nghiên cứu', ''),
        ('Test tính năng cũ', 'Kiểm thử các chức năng chính', -10, -3, 'Thấp', 'Tạm hoãn', 'Công việc', 'Tạm dừng chờ phản hồi'),
        ('Cập nhật banner', 'Thay ảnh banner chiến dịch', -3, -1, 'Cao', 'Đang làm', 'Marketing', 'Đang quá hạn'),
    ]
    for name, desc, s, d, pr, st, gr, note in samples:
        db.session.add(Task(name=name, description=desc, start_date=today+timedelta(days=s), due_date=today+timedelta(days=d), priority=pr, status=st, group_name=gr, notes=note))
    db.session.commit()


def filtered_query():
    q = Task.query
    search = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    priority = request.args.get('priority', '').strip()
    group_name = request.args.get('group', '').strip()
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Task.name.like(like), Task.description.like(like), Task.notes.like(like)))
    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)
    if group_name:
        q = q.filter(Task.group_name == group_name)
    return q


def stats():
    tasks = Task.query.all()
    total = len(tasks)
    done = sum(t.status == 'Hoàn thành' for t in tasks)
    doing = sum(t.status == 'Đang làm' for t in tasks)
    overdue = sum(t.is_overdue for t in tasks)
    rate = round(done / total * 100) if total else 0
    return dict(total=total, done=done, doing=doing, overdue=overdue, rate=rate)

@app.before_request
def init_db():
    ensure_seed_data()

@app.route('/')
def dashboard():
    s = stats()
    upcoming = Task.query.order_by(Task.due_date.asc()).limit(5).all()
    tasks = Task.query.all()
    by_status = {st: sum(t.status == st for t in tasks) for st in STATUSES}
    week_labels, week_rates = week_performance(date.today())
    return render_template('dashboard.html', active='dashboard', stats=s, upcoming=upcoming, by_status=by_status, week_labels=week_labels, week_rates=week_rates)

@app.route('/tasks')
def tasks():
    items = filtered_query().order_by(Task.due_date.asc()).all()
    return render_template('tasks.html', active='tasks', tasks=items, statuses=STATUSES, priorities=PRIORITIES, groups=GROUPS, today=date.today())

@app.route('/tasks/save', methods=['POST'])
def save_task():
    task_id = request.form.get('id')
    task = Task.query.get(task_id) if task_id else Task()
    task.name = request.form['name']
    task.description = request.form.get('description', '')
    task.start_date = parse_date(request.form.get('start_date'))
    task.due_date = parse_date(request.form.get('due_date'))
    task.priority = request.form.get('priority', 'Trung bình')
    task.status = request.form.get('status', 'Chưa bắt đầu')
    task.group_name = request.form.get('group_name', 'Công việc')
    task.notes = request.form.get('notes', '')
    db.session.add(task)
    db.session.commit()
    return redirect(url_for('tasks'))

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('tasks'))

@app.route('/week')
def week():
    base = parse_date(request.args.get('date'), date.today())
    monday = base - timedelta(days=base.weekday())
    days = [monday + timedelta(days=i) for i in range(7)]
    data = {d: Task.query.filter(Task.start_date <= d, Task.due_date >= d).order_by(Task.due_date).all() for d in days}
    return render_template('week.html', active='week', days=days, data=data, prev=monday-timedelta(days=7), nxt=monday+timedelta(days=7))

@app.route('/month')
def month():
    base = parse_date(request.args.get('date'), date.today())
    first = base.replace(day=1)
    start = first - timedelta(days=first.weekday())
    weeks = []
    cur = start
    for _ in range(6):
        row = []
        for _ in range(7):
            row.append((cur, Task.query.filter(Task.start_date <= cur, Task.due_date >= cur).all()))
            cur += timedelta(days=1)
        weeks.append(row)
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first.replace(day=monthrange(first.year, first.month)[1]) + timedelta(days=1)).replace(day=1)
    return render_template('month.html', active='month', weeks=weeks, base=base, prev=prev_month, nxt=next_month)

@app.route('/reports')
def reports():
    s = stats()
    week_labels, week_rates = week_performance(date.today())
    month_labels, month_rates = month_performance(date.today())
    return render_template('reports.html', active='reports', stats=s, week_labels=week_labels, week_rates=week_rates, month_labels=month_labels, month_rates=month_rates)

def week_performance(base):
    monday = base - timedelta(days=base.weekday())
    labels, rates = [], []
    for i in range(7):
        d = monday + timedelta(days=i)
        items = Task.query.filter(Task.due_date <= d).all()
        done = sum(t.status == 'Hoàn thành' for t in items)
        labels.append(['T2','T3','T4','T5','T6','T7','CN'][i])
        rates.append(round(done / len(items) * 100) if items else 0)
    return labels, rates

def month_performance(base):
    labels, rates = [], []
    for i in range(1, 13):
        start = date(base.year, i, 1)
        end = date(base.year, i, monthrange(base.year, i)[1])
        items = Task.query.filter(Task.due_date >= start, Task.due_date <= end).all()
        done = sum(t.status == 'Hoàn thành' for t in items)
        labels.append(f'T{i}')
        rates.append(round(done / len(items) * 100) if items else 0)
    return labels, rates

@app.template_filter('datevn')
def datevn(d):
    return d.strftime('%d/%m/%Y') if d else ''

if __name__ == '__main__':
    app.run()
