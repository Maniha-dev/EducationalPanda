import flet as ft
import re, json, os, hashlib
from collections import deque, Counter
from math import ceil

# =============================
# DATA STRUCTURE 1: TRIE (Prefix Search)
# =============================
class TrieNode:
    def __init__(self):
        self.children = {}
        self.uni_ids = []

class UniversityTrie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, name, uni_id):
        node = self.root
        for char in name.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            if uni_id not in node.uni_ids:
                node.uni_ids.append(uni_id)

    def search(self, prefix):
        node = self.root
        for char in prefix.lower():
            if char not in node.children: 
                return []
            node = node.children[char]
        return list(set(node.uni_ids))

uni_trie = UniversityTrie()

# =============================
# DATA STRUCTURE 2: GRAPH (Recommendations)
# =============================
class CourseRecommendationGraph:
    def __init__(self):
        # Adjacency List: { "Course A": {"Course B", "Course C"} }
        self.adj_list = {}

    def build_graph(self, all_enrollments):
        """
        Builds a graph where nodes are courses and edges exist 
        if the same student took both courses.
        """
        self.adj_list = {}
        
        # 1. Group courses by student
        # all_enrollments format: {'user@email.com': ['Python', 'Web Dev'], ...}
        for student, courses in all_enrollments.items():
            # Create edges between every pair of courses a student has taken
            for i in range(len(courses)):
                for j in range(i + 1, len(courses)):
                    u, v = courses[i], courses[j]
                    self.add_edge(u, v)

    def add_edge(self, u, v):
        if u not in self.adj_list: self.adj_list[u] = []
        if v not in self.adj_list: self.adj_list[v] = []
        self.adj_list[u].append(v)
        self.adj_list[v].append(u)

    def recommend_bfs(self, user_courses, limit=3):
        """
        Uses BFS to find courses connected to the user's current courses.
        """
        if not user_courses: return []

        queue = deque(user_courses)
        visited = set(user_courses)
        recommendations = []
        
        # We use a Counter to prioritize courses that appear more frequently (stronger connections)
        candidate_counts = Counter()

        # BFS (Depth 1 is usually enough for "People who bought this also bought...")
        while queue:
            current_course = queue.popleft()
            
            if current_course in self.adj_list:
                neighbors = self.adj_list[current_course]
                for neighbor in neighbors:
                    if neighbor not in visited:
                        candidate_counts[neighbor] += 1
                        # We don't add neighbors to queue here to keep it strictly 
                        # "immediate connections" for relevance, but standard BFS would add them.
        
        # Sort by most common connections
        most_common = candidate_counts.most_common(limit)
        return [course for course, count in most_common]

rec_graph = CourseRecommendationGraph()

# =============================
# FILE PATHS & UTILITIES
# =============================
USERS_FILE = "users.json"
COURSES_FILE = "courses.json"
ENROLL_FILE = "enrollments.json"
QUEUE_FILE = "queues.json"
UNIVERSITIES_FILE = "universities.json" 
PAGE_SIZE = 5 

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email)

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f: return json.load(f)
        except: return default
    return default

def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f, indent=4)
    except IOError as e: print(f"Error saving {path}: {e}")

# =============================
# DATABASE LOADING
# =============================
users_db = load_json(USERS_FILE, {"admin@edupanda.com": {"name": "General Admin", "uni": "EduPanda HQ", "hash": hash_password("admin123")}})
universities_db = load_json(UNIVERSITIES_FILE, {
    "uni_harvard": {"name": "Harvard University", "loc": "USA", "details": "Ivy League.", "admin_email": "harvard@edupanda.com", "admin_hash": hash_password("uni123")},
    "uni_oxford": {"name": "University of Oxford", "loc": "UK", "details": "Oldest English uni.", "admin_email": "oxford@edupanda.com", "admin_hash": hash_password("uni123")},
    "uni_lums": {"name": "LUMS", "loc": "Pakistan", "details": "Leading research uni.", "admin_email": "lums@edupanda.com", "admin_hash": hash_password("uni123")},
    "uni_tokyo": {"name": "University of Tokyo", "loc": "Japan", "details": "Premier Asian uni.", "admin_email": "tokyo@edupanda.com", "admin_hash": hash_password("uni123")}
})

# Populate Trie
for u_id, u_data in universities_db.items():
    uni_trie.insert(u_data['name'], u_id)
    uni_trie.insert(u_data['loc'], u_id)

courses_db = load_json(COURSES_FILE, [
    {"title": "Python for Data Science", "price": 0, "desc": "Learn basic analysis.", "uni_id": "uni_harvard", "capacity": 50},
    {"title": "Web Development", "price": 15, "desc": "Learn Flet & React.", "uni_id": "uni_lums", "capacity": 100},
    {"title": "Cloud Computing Basics", "price": 50, "desc": "Introduction to AWS.", "uni_id": "uni_oxford", "capacity": 30},
    {"title": "Machine Learning Ethics", "price": 0, "desc": "Study the impact of AI.", "uni_id": "uni_tokyo", "capacity": 10}
])

conference_queues = load_json(QUEUE_FILE, {
    "Global AI Summit": {"uni_id": "uni_harvard", "attendees": []},
    "EduTech World": {"uni_id": "uni_lums", "attendees": []},
})

user_enrollments = load_json(ENROLL_FILE, {})

# Build the Graph initially
rec_graph.build_graph(user_enrollments)

current_user = None
current_uni_id = None 

# =============================
# MAIN APP
# =============================
def main(page: ft.Page):
    global current_user, current_uni_id

    page.title = "EduPanda"
    page.window_width = 380
    page.window_height = 700
    page.bgcolor = ft.Colors.WHITE 
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.ORANGE_700) 
    page.snack_bar = ft.SnackBar(content=ft.Text(""), duration=1500)

    def show_snackbar(message, color=ft.Colors.GREEN_700):
        page.snack_bar.content = ft.Text(message, color=ft.Colors.WHITE)
        page.snack_bar.bgcolor = color
        page.snack_bar.open = True
        page.update()

    # --- UI Elements ---
    login_email = ft.TextField(label="Email", width=300, prefix_icon=ft.Icons.EMAIL)
    login_pass = ft.TextField(label="Password", password=True, width=300, prefix_icon=ft.Icons.LOCK)

    signup_name = ft.TextField(label="Full Name", width=300)
    signup_email = ft.TextField(label="Enter Email", width=300)
    signup_pass = ft.TextField(label="Set Password", password=True, width=300)
    signup_confirm = ft.TextField(label="Confirm Password", password=True, width=300)
    signup_university = ft.Dropdown(label="Affiliated University", width=300, options=[ft.dropdown.Option(u["name"]) for u in universities_db.values()])

    uni_dash_name = ft.TextField(label="University Name", width=300)
    uni_dash_loc = ft.TextField(label="Location", width=300)
    uni_dash_details = ft.TextField(label="Description", width=300, multiline=True)
    
    uni_new_course_title = ft.TextField(label="Course Title", width=280, text_size=12)
    uni_new_course_price = ft.TextField(label="Price", width=280, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)
    uni_new_course_desc = ft.TextField(label="Description", width=280, text_size=12, multiline=True)
    uni_new_course_capacity = ft.TextField(label="Max Seats", width=280, text_size=12, keyboard_type=ft.KeyboardType.NUMBER) 
    uni_new_conference_title = ft.TextField(label="Conference Title", width=280, text_size=12)

    search_box = ft.TextField(label="Search University...", width=250, border_radius=20, suffix_icon=ft.Icons.SEARCH)
    results_view = ft.ListView(expand=True, spacing=10, padding=20)

    # --- HELPERS ---
    def paginate(items, page_no, page_size=PAGE_SIZE):
        start = (page_no - 1) * page_size
        return items[start:start + page_size]
    
    def get_course_enrollment_count(course_title):
        count = 0
        for enrollments in user_enrollments.values():
            if course_title in enrollments: count += 1
        return count

    # --- ACTION HANDLERS ---
    def enroll_course(e, course_index, course_title):
        course = courses_db[course_index]
        if get_course_enrollment_count(course_title) >= course.get("capacity", 9999): 
            show_snackbar("Course is full!", ft.Colors.RED_700); return

        user_set = set(user_enrollments.get(current_user, []))
        if course_title in user_set:
            show_snackbar("Already enrolled!", ft.Colors.BLUE_GREY_700)
        else:
            user_set.add(course_title)
            user_enrollments[current_user] = list(user_set)
            save_json(ENROLL_FILE, user_enrollments)
            # Rebuild graph on new enrollment to keep recommendations fresh
            rec_graph.build_graph(user_enrollments)
            show_snackbar(f"Enrolled in {course_title}!", ft.Colors.GREEN_700)
        page.update()

    def join_queue(e, conf_title):
        queue = conference_queues[conf_title]["attendees"]
        if current_user in queue:
            show_snackbar("Already applied!", ft.Colors.BLUE_GREY_700)
        else:
            queue.append(current_user)
            save_json(QUEUE_FILE, conference_queues)
            show_snackbar("Applied successfully!", ft.Colors.GREEN_700)
        page.update()
        
    def search_university(e):
        query = search_box.value.strip().lower()
        results_view.controls.clear()
        target_ids = uni_trie.search(query) if query else list(universities_db.keys())

        if not target_ids:
            results_view.controls.append(ft.Text("No matches found.", color=ft.Colors.RED_700))
        else:
            for uni_id in target_ids:
                uni = universities_db[uni_id]
                course_count = len([c for c in courses_db if c.get("uni_id") == uni_id])
                results_view.controls.append(
                    ft.Card(content=ft.Container(padding=15, content=ft.Column([
                        ft.Text(uni['name'], size=18, weight="bold"),
                        ft.Text(f"Loc: {uni['loc']} | Courses: {course_count}", size=12),
                    ])), width=350)
                )
        page.update()

    # --- AUTH HANDLERS ---
    def handle_signup(e):
        email = signup_email.value.strip()
        pwd = signup_pass.value
        if email in users_db:
            signup_email.error_text = "User exists"
        elif pwd != signup_confirm.value:
            signup_pass.error_text = "Mismatch"
        else:
            users_db[email] = {"name": signup_name.value, "uni": signup_university.value, "hash": hash_password(pwd)}
            user_enrollments.setdefault(email, [])
            save_json(USERS_FILE, users_db)
            save_json(ENROLL_FILE, user_enrollments)
            show_snackbar("Registered! Login now.")
            page.go("/login")
        page.update()

    def handle_login(e):
        global current_user, current_uni_id
        current_user = None
        current_uni_id = None
        email = login_email.value.strip()
        pwd = login_pass.value
        
        # Student Login
        if email in users_db and verify_password(pwd, users_db[email].get("hash")):
            current_user = email
            user_enrollments.setdefault(email, [])
            page.go("/dashboard")
            return

        # Uni Admin Login
        for uni_id, uni_data in universities_db.items():
            if uni_data.get("admin_email") == email and verify_password(pwd, uni_data.get("admin_hash")):
                current_uni_id = uni_id
                page.go("/uni-dashboard")
                return

        login_email.error_text = "Invalid credentials"
        page.update()

    # --- UNI ADMIN HANDLERS (Briefed) ---
    def update_university_details(e):
        universities_db[current_uni_id]["name"] = uni_dash_name.value
        universities_db[current_uni_id]["loc"] = uni_dash_loc.value
        universities_db[current_uni_id]["details"] = uni_dash_details.value
        uni_trie.insert(uni_dash_name.value, current_uni_id)
        save_json(UNIVERSITIES_FILE, universities_db)
        show_snackbar("Details Updated")

    def add_course_by_uni_admin(e):
        courses_db.append({
            "title": uni_new_course_title.value,
            "price": int(uni_new_course_price.value),
            "desc": uni_new_course_desc.value,
            "uni_id": current_uni_id,
            "capacity": int(uni_new_course_capacity.value)
        })
        save_json(COURSES_FILE, courses_db)
        show_snackbar("Course Added")
        route_change(page.route)

    def delete_course(e, idx, title):
        global courses_db, user_enrollments
        for email, enrolled in user_enrollments.items():
            if title in enrolled: enrolled.remove(title)
        courses_db.pop(idx)
        save_json(COURSES_FILE, courses_db)
        save_json(ENROLL_FILE, user_enrollments)
        route_change("/uni-dashboard")

    # =============================
    # ROUTING
    # =============================
    def route_change(route):
        page.views.clear()

        def create_centered_view(route_name, controls):
            return ft.View(route_name, [ft.Column(controls, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)], horizontal_alignment="center", vertical_alignment="center")

        if page.route in ["/", "/login"]:
            page.views.append(create_centered_view("/login", [
                ft.Text("EduPanda Login", size=24, weight="bold", color=ft.Colors.ORANGE_700),
                login_email, login_pass,
                ft.ElevatedButton("LOGIN", on_click=handle_login),
                ft.TextButton("Register Student", on_click=lambda _: page.go("/signup"))
            ]))

        elif page.route == "/signup":
            page.views.append(create_centered_view("/signup", [
                ft.Text("Register", size=24, weight="bold"),
                signup_name, signup_university, signup_email, signup_pass, signup_confirm,
                ft.ElevatedButton("REGISTER", on_click=handle_signup)
            ]))

        elif page.route == "/uni-dashboard":
            if not current_uni_id: page.go("/login"); return
            # ... (Simplified Admin UI for brevity, same logic as before) ...
            uni_courses = [(i, c) for i, c in enumerate(courses_db) if c.get("uni_id") == current_uni_id]
            course_cards = [
                ft.Card(ft.Container(padding=10, content=ft.Column([
                    ft.Text(c['title'], weight="bold"),
                    ft.IconButton(ft.Icons.DELETE, on_click=lambda e, i=i, t=c['title']: delete_course(e, i, t))
                ]))) for i, c in uni_courses
            ]
            
            page.views.append(ft.View("/uni-dashboard", [
                ft.AppBar(title=ft.Text("Uni Admin"), bgcolor=ft.Colors.ORANGE_700),
                ft.Column([
                    ft.Text("Update Details", weight="bold"),
                    uni_dash_name, uni_dash_loc, uni_dash_details,
                    ft.ElevatedButton("Save", on_click=update_university_details),
                    ft.Divider(),
                    ft.Text("Add Course", weight="bold"),
                    uni_new_course_title, uni_new_course_price, uni_new_course_capacity, uni_new_course_desc,
                    ft.ElevatedButton("Add", on_click=add_course_by_uni_admin),
                    ft.Divider(),
                    *course_cards,
                    ft.ElevatedButton("Logout", on_click=lambda _: page.go("/login"))
                ], scroll=ft.ScrollMode.AUTO)
            ]))

        elif page.route == "/dashboard":
            if not current_user: page.go("/login"); return
            
            # --- RECOMMENDATION ENGINE LOGIC ---
            my_courses = user_enrollments.get(current_user, [])
            recommended_titles = rec_graph.recommend_bfs(my_courses)
            
            rec_cards = []
            if not recommended_titles:
                rec_cards.append(ft.Text("No recommendations yet. Enroll in courses to get suggestions!", size=12, italic=True, color=ft.Colors.GREY))
            else:
                for title in recommended_titles:
                    rec_cards.append(
                        ft.Card(ft.Container(padding=10, content=ft.Row([
                            ft.Icon(ft.Icons.LIGHTBULB, color=ft.Colors.YELLOW_800),
                            ft.Column([
                                ft.Text(title, weight="bold"),
                                ft.Text("Based on your history", size=10, color=ft.Colors.GREY)
                            ])
                        ])), width=300)
                    )

            page.views.append(create_centered_view("/dashboard", [
                ft.Text(f"Welcome, {users_db[current_user].get('name')}", size=22, color=ft.Colors.ORANGE_700),
                
                # --- NEW RECOMMENDATION SECTION ---
                ft.Container(
                    content=ft.Column([
                        ft.Text("🎯 Recommended for You", weight="bold", size=16),
                        *rec_cards
                    ], spacing=10),
                    padding=10, border=ft.border.all(1, ft.Colors.ORANGE_200), border_radius=10, bgcolor=ft.Colors.ORANGE_50
                ),
                # ----------------------------------

                ft.ElevatedButton("My Profile", icon=ft.Icons.PERSON, on_click=lambda _: page.go("/profile")), 
                ft.ElevatedButton("Browse Courses", icon=ft.Icons.LIBRARY_BOOKS, on_click=lambda _: page.go("/courses?1")),
                ft.ElevatedButton("Conferences", icon=ft.Icons.GROUP, on_click=lambda _: page.go("/conferences")),
                ft.ElevatedButton("Uni Directory", icon=ft.Icons.LOCATION_CITY, on_click=lambda _: page.go("/universities")),
                ft.ElevatedButton("Logout", on_click=lambda _: page.go("/login"))
            ]))

        elif page.route.startswith("/courses"):
            # ... (Standard Course Catalog Logic) ...
            page_no = int(page.route.split("?")[-1]) if "?" in page.route else 1
            sorted_courses = sorted(courses_db, key=lambda x: x["title"])
            course_cards = []
            for c in sorted_courses:
                try: idx = courses_db.index(c)
                except: continue
                enrolled = c["title"] in user_enrollments.get(current_user, [])
                btn = ft.Text("Enrolled", color="green") if enrolled else ft.ElevatedButton("Enroll", on_click=lambda e, i=idx, t=c["title"]: enroll_course(e, i, t))
                course_cards.append(ft.Card(ft.Container(padding=10, content=ft.Column([
                    ft.Text(c["title"], weight="bold"), ft.Text(f"${c['price']}"), ft.Text(c["desc"], size=12), btn
                ]))))
            
            page.views.append(ft.View("/courses", [
                ft.AppBar(title=ft.Text("Courses"), bgcolor=ft.Colors.ORANGE_700),
                ft.ListView(paginate(course_cards, page_no), expand=True),
                ft.Row([
                    ft.IconButton(ft.Icons.NAVIGATE_BEFORE, on_click=lambda _: page.go(f"/courses?{page_no-1}")),
                    ft.IconButton(ft.Icons.NAVIGATE_NEXT, on_click=lambda _: page.go(f"/courses?{page_no+1}"))
                ], alignment="center"),
                ft.ElevatedButton("Back", on_click=lambda _: page.go("/dashboard"))
            ]))

        # (Other routes like /profile, /conferences, /universities remain standard...)
        elif page.route == "/profile":
             # Simplified Profile View
             page.views.append(ft.View("/profile", [
                 ft.AppBar(title=ft.Text("Profile"), bgcolor=ft.Colors.ORANGE_700),
                 ft.Column([
                     ft.Text(f"User: {current_user}", size=20),
                     ft.Text("Enrolled Courses:", weight="bold"),
                     *[ft.Text(c) for c in user_enrollments.get(current_user, [])],
                     ft.ElevatedButton("Back", on_click=lambda _: page.go("/dashboard"))
                 ], alignment="center", horizontal_alignment="center")
             ]))
        
        elif page.route == "/conferences":
             page.views.append(ft.View("/conferences", [
                 ft.AppBar(title=ft.Text("Conferences"), bgcolor=ft.Colors.ORANGE_700),
                 ft.Column([
                     *[ft.Card(ft.Container(padding=10, content=ft.Column([
                         ft.Text(k, weight="bold"), 
                         ft.ElevatedButton("Join Queue", on_click=lambda e, k=k: join_queue(e, k))
                     ]))) for k in conference_queues],
                     ft.ElevatedButton("Back", on_click=lambda _: page.go("/dashboard"))
                 ])
             ]))

        elif page.route == "/universities":
            search_box.on_change = search_university
            page.views.append(ft.View("/universities", [
                ft.AppBar(title=ft.Text("Universities"), bgcolor=ft.Colors.ORANGE_700),
                ft.Column([search_box, results_view, ft.ElevatedButton("Back", on_click=lambda _: page.go("/dashboard"))])
            ]))

        page.update()

    page.on_route_change = route_change
    page.go("/login")

ft.app(target=main)