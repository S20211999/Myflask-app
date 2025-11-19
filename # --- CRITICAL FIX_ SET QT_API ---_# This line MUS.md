Here are the remaining JavaScript files to complete your project management application:

## 17. public/js/app.js

```javascript
const API_URL = 'http://localhost:3000/api';

// Tab switching
document.addEventListener('DOMContentLoaded', () => {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const forms = document.querySelectorAll('.auth-form');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            forms.forEach(f => f.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${tab}Form`).classList.add('active');
        });
    });

    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            // Store token and user data
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));

            // Redirect to dashboard
            window.location.href = 'dashboard.html';
        } catch (error) {
            showError(error.message);
        }
    });

    // Register form
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = document.getElementById('registerName').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const role = document.getElementById('registerRole').value;

        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, email, password, role })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Registration failed');
            }

            // Store token and user data
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));

            // Redirect to dashboard
            window.location.href = 'dashboard.html';
        } catch (error) {
            showError(error.message);
        }
    });
});

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Utility function to make authenticated API calls
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    };

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    });

    if (response.status === 401) {
        localStorage.clear();
        window.location.href = 'index.html';
        return;
    }

    return response;
}

// Check authentication
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'No date';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Get priority color class
function getPriorityClass(priority) {
    const classes = {
        low: 'priority-low',
        medium: 'priority-medium',
        high: 'priority-high',
        critical: 'priority-critical'
    };
    return classes[priority] || 'priority-medium';
}
```

## 18. public/js/dashboard.js

```javascript
const API_URL = 'http://localhost:3000/api';
let socket;
let taskDistChart;
let projectProgressChart;

document.addEventListener('DOMContentLoaded', async () => {
    checkAuth();
    loadUserInfo();
    setupEventListeners();
    await loadDashboardData();
    initializeCharts();
    connectSocket();
});

function loadUserInfo() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (user) {
        document.getElementById('userName').textContent = user.name;
        document.getElementById('userRole').textContent = user.role;
        document.getElementById('userAvatar').src = user.avatar;
    }
}

function setupEventListeners() {
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.clear();
        window.location.href = 'index.html';
    });

    // Create project modal
    const modal = document.getElementById('projectModal');
    const createBtn = document.getElementById('createProjectBtn');
    const closeBtn = document.querySelector('.close');

    createBtn.addEventListener('click', () => {
        modal.classList.add('active');
    });

    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });

    // Project form submission
    document.getElementById('projectForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await createProject();
    });
}

async function loadDashboardData() {
    try {
        // Load projects
        const projectsResponse = await apiCall('/projects');
        const projects = await projectsResponse.json();

        // Load all tasks
        const tasksResponse = await apiCall('/tasks');
        const tasks = await tasksResponse.json();

        // Update stats
        updateStats(projects, tasks);
        
        // Update charts
        updateCharts(tasks, projects);
        
        // Display recent tasks
        displayRecentTasks(tasks.slice(0, 10));

    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateStats(projects, tasks) {
    document.getElementById('totalProjects').textContent = projects.length;
    
    const activeTasks = tasks.filter(t => t.status !== 'completed').length;
    document.getElementById('activeTasks').textContent = activeTasks;
    
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    document.getElementById('completedTasks').textContent = completedTasks;
    
    const overdueTasks = tasks.filter(t => 
        t.dueDate && new Date(t.dueDate) < new Date() && t.status !== 'completed'
    ).length;
    document.getElementById('overdueTasks').textContent = overdueTasks;
}

function initializeCharts() {
    // Task Distribution Chart
    const taskDistCtx = document.getElementById('taskDistChart').getContext('2d');
    taskDistChart = new Chart(taskDistCtx, {
        type: 'doughnut',
        data: {
            labels: ['To Do', 'In Progress', 'Review', 'Completed'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    '#3b82f6',
                    '#f59e0b',
                    '#8b5cf6',
                    '#10b981'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Project Progress Chart
    const projectProgressCtx = document.getElementById('projectProgressChart').getContext('2d');
    projectProgressChart = new Chart(projectProgressCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Progress %',
                data: [],
                backgroundColor: '#4f46e5'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function updateCharts(tasks, projects) {
    // Update task distribution chart
    const taskCounts = {
        todo: tasks.filter(t => t.status === 'todo').length,
        inProgress: tasks.filter(t => t.status === 'in-progress').length,
        review: tasks.filter(t => t.status === 'review').length,
        completed: tasks.filter(t => t.status === 'completed').length
    };

    taskDistChart.data.datasets[0].data = [
        taskCounts.todo,
        taskCounts.inProgress,
        taskCounts.review,
        taskCounts.completed
    ];
    taskDistChart.update();

    // Update project progress chart
    const projectNames = projects.slice(0, 5).map(p => p.name);
    const projectProgress = projects.slice(0, 5).map(p => p.progress || 0);

    projectProgressChart.data.labels = projectNames;
    projectProgressChart.data.datasets[0].data = projectProgress;
    projectProgressChart.update();
}

function displayRecentTasks(tasks) {
    const container = document.getElementById('recentTasksList');
    
    if (tasks.length === 0) {
        container.innerHTML = '<p style="color: #6b7280; text-align: center;">No tasks yet</p>';
        return;
    }

    container.innerHTML = tasks.map(task => `
        <div class="task-card" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <span class="task-priority ${getPriorityClass(task.priority)}">${task.priority}</span>
                    <div class="task-title">${task.title}</div>
                    <p style="font-size: 14px; color: #6b7280; margin-top: 4px;">
                        ${task.description || 'No description'}
                    </p>
                </div>
                <span style="font-size: 12px; color: #6b7280;">
                    ${formatDate(task.dueDate)}
                </span>
            </div>
            <div class="task-meta">
                <div class="task-assignee">
                    ${task.assignedTo ? `
                        <img src="${task.assignedTo.avatar}" alt="${task.assignedTo.name}">
                        <span>${task.assignedTo.name}</span>
                    ` : '<span>Unassigned</span>'}
                </div>
                <span style="text-transform: capitalize;">${task.status.replace('-', ' ')}</span>
            </div>
        </div>
    `).join('');
}

async function createProject() {
    const projectData = {
        name: document.getElementById('projectName').value,
        description: document.getElementById('projectDescription').value,
        startDate: document.getElementById('projectStartDate').value,
        endDate: document.getElementById('projectEndDate').value,
        priority: document.getElementById('projectPriority').value,
        budget: parseFloat(document.getElementById('projectBudget').value) || 0
    };

    try {
        const response = await apiCall('/projects', {
            method: 'POST',
            body: JSON.stringify(projectData)
        });

        if (response.ok) {
            document.getElementById('projectModal').classList.remove('active');
            document.getElementById('projectForm').reset();
            await loadDashboardData();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to create project');
        }
    } catch (error) {
        console.error('Error creating project:', error);
        alert('Failed to create project');
    }
}

function connectSocket() {
    socket = io('http://localhost:3000');

    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('task:created', () => {
        loadDashboardData();
    });

    socket.on('task:updated', () => {
        loadDashboardData();
    });

    socket.on('task:deleted', () => {
        loadDashboardData();
    });
}
```

## 19. public/js/kanban.js

```javascript
const API_URL = 'http://localhost:3000/api';
let socket;
let allTasks = [];
let allProjects = [];
let allUsers = [];
let draggedTask = null;

document.addEventListener('DOMContentLoaded', async () => {
    checkAuth();
    setupEventListeners();
    await loadInitialData();
    connectSocket();
});

function setupEventListeners() {
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        localStorage.clear();
        window.location.href = 'index.html';
    });

    // Project filter
    document.getElementById('projectFilter').addEventListener('change', (e) => {
        const projectId = e.target.value;
        filterTasksByProject(projectId);
    });

    // Create task modal
    const modal = document.getElementById('taskModal');
    const createBtn = document.getElementById('createTaskBtn');
    const closeBtn = document.querySelector('.close');

    createBtn.addEventListener('click', () => {
        resetTaskForm();
        document.getElementById('taskModalTitle').textContent = 'Create New Task';
        modal.classList.add('active');
    });

    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('active');
        }
    });

    // Task form submission
    document.getElementById('taskForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveTask();
    });

    // Setup drag and drop for columns
    setupDragAndDrop();
}

function setupDragAndDrop() {
    const columns = document.querySelectorAll('.task-list');

    columns.forEach(column => {
        column.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            column.style.background = '#e0e7ff';
        });

        column.addEventListener('dragleave', () => {
            column.style.background = '';
        });

        column.addEventListener('drop', async (e) => {
            e.preventDefault();
            column.style.background = '';
            
            const taskId = e.dataTransfer.getData('text/plain');
            const newStatus = column.closest('.kanban-column').dataset.status;
            
            await updateTaskStatus(taskId, newStatus);
        });
    });
}

async function loadInitialData() {
    try {
        // Load projects
        const projectsResponse = await apiCall('/projects');
        allProjects = await projectsResponse.json();
        populateProjectFilter();
        populateProjectDropdown();

        // Load users
        const usersResponse = await apiCall('/auth/users');
        allUsers = await usersResponse.json();
        populateUserDropdown();

        // Load tasks
        await loadTasks();

    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

function populateProjectFilter() {
    const select = document.getElementById('projectFilter');
    select.innerHTML = '<option value="">All Projects</option>';
    
    allProjects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = project.name;
        select.appendChild(option);
    });
}

function populateProjectDropdown() {
    const select = document.getElementById('taskProject');
    select.innerHTML = '<option value="">Select Project</option>';
    
    allProjects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = project.name;
        select.appendChild(option);
    });
}

function populateUserDropdown() {
    const select = document.getElementById('taskAssignee');
    select.innerHTML = '<option value="">Unassigned</option>';
    
    allUsers.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = `${user.name} (${user.role})`;
        select.appendChild(option);
    });
}

async function loadTasks(projectId = null) {
    try {
        const url = projectId ? `/tasks?projectId=${projectId}` : '/tasks';
        const response = await apiCall(url);
        allTasks = await response.json();
        
        renderTasks();
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function filterTasksByProject(projectId) {
    if (projectId) {
        loadTasks(projectId);
    } else {
        loadTasks();
    }
}

function renderTasks() {
    // Clear all columns
    ['todo', 'in-progress', 'review', 'completed'].forEach(status => {
        const listId = status === 'in-progress' ? 'inProgressList' : 
                       status === 'todo' ? 'todoList' :
                       status === 'review' ? 'reviewList' : 'completedList';
        document.getElementById(listId).innerHTML = '';
    });

    // Group tasks by status
    const tasksByStatus = {
        'todo': [],
        'in-progress': [],
        'review': [],
        'completed': []
    };

    allTasks.forEach(task => {
        if (tasksByStatus[task.status]) {
            tasksByStatus[task.status].push(task);
        }
    });

    // Render tasks in each column
    Object.keys(tasksByStatus).forEach(status => {
        const tasks = tasksByStatus[status];
        const listId = status === 'in-progress' ? 'inProgressList' : 
                       status === 'todo' ? 'todoList' :
                       status === 'review' ? 'reviewList' : 'completedList';
        const countId = status === 'in-progress' ? 'inProgressCount' : 
                        status === 'todo' ? 'todoCount' :
                        status === 'review' ? 'reviewCount' : 'completedCount';
        
        document.getElementById(countId).textContent = tasks.length;
        
        const list = document.getElementById(listId);
        list.innerHTML = tasks.map(task => createTaskCard(task)).join('');
    });

    // Add drag event listeners to task cards
    document.querySelectorAll('.task-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', card.dataset.taskId);
            card.classList.add('dragging');
        });

        card.addEventListener('dragend', (e) => {
            card.classList.remove('dragging');
        });

        card.addEventListener('click', () => {
            openEditTaskModal(card.dataset.taskId);
        });
    });
}

function createTaskCard(task) {
    return `
        <div class="task-card" draggable="true" data-task-id="${task.id}">
            <span class="task-priority ${getPriorityClass(task.priority)}">
                ${task.priority}
            </span>
            <div class="task-title">${task.title}</div>
            ${task.description ? `<p style="font-size: 13px; color: #6b7280; margin-top: 6px;">${task.description.substring(0, 80)}${task.description.length > 80 ? '...' : ''}</p>` : ''}
            <div class="task-meta">
                <div class="task-assignee">
                    ${task.assignedTo ? `
                        <img src="${task.assignedTo.avatar}" alt="${task.assignedTo.name}">
                        <span>${task.assignedTo.name}</span>
                    ` : '<span>Unassigned</span>'}
                </div>
                ${task.dueDate ? `<span>📅 ${formatDate(task.dueDate)}</span>` : ''}
            </div>
        </div>
    `;
}

async function updateTaskStatus(taskId, newStatus) {
    try {
        const response = await apiCall(`/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            const task = allTasks.find(t => t.id === taskId);
            if (task) {
                task.status = newStatus;
            }
            renderTasks();
        }
    } catch (error) {
        console.error('Error updating task status:', error);
    }
}

function resetTaskForm() {
    document.getElementById('taskForm').reset();
    document.getElementById('taskId').value = '';
}

function openEditTaskModal(taskId) {
    const task = allTasks.find(t => t.id === taskId);
    if (!task) return;

    document.getElementById('taskModalTitle').textContent = 'Edit Task';
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskProject').value = task.projectId || '';
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDescription').value = task.description || '';
    document.getElementById('taskAssignee').value = task.assignedToId || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDueDate').value = task.dueDate ? task.dueDate.split('T')[0] : '';
    document.getElementById('taskEstimatedHours').value = task.estimatedHours || '';

    document.getElementById('taskModal').classList.add('active');
}

async function saveTask() {
    const taskId = document.getElementById('taskId').value;
    const taskData = {
        projectId: document.getElementById('taskProject').value,
        title: document.getElementById('taskTitle').value,
        description: document.getElementById('taskDescription').value,
        assignedToId: document.getElementById('taskAssignee').value || null,
        priority: document.getElementById('taskPriority').value,
        dueDate: document.getElementById('taskDueDate').value || null,
        estimatedHours: parseFloat(document.getElementById('taskEstimatedHours').value) || 0
    };

    try {
        let response;
        if (taskId) {
            // Update existing task
            response = await apiCall(`/tasks/${taskId}`, {
                method: 'PUT',
                body: JSON.stringify(taskData)
            });
        } else {
            // Create new task
            response = await apiCall('/tasks', {
                method: 'POST',
                body: JSON.stringify(taskData)
            });
        }

        if (response.ok) {
            document.getElementById('taskModal').classList.remove('active');
            await loadTasks();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to save task');
        }
    } catch (error) {
        console.error('Error saving task:', error);
        alert('Failed to save task');
    }
}

function connectSocket() {
    socket = io('http://localhost:3000');

    socket.on('connect', () => {
        console.log('Connected to server');
    });

    socket.on('task:created', (task) => {
        allTasks.push(task);
        renderTasks();
    });

    socket.on('task:updated', (updatedTask) => {
        const index = allTasks.findIndex(t => t.id === updatedTask.id);
        if (index !== -1) {
            allTasks[index] = updatedTask;
            renderTasks();
        }
    });

    socket.on('task:deleted', (data) => {
        allTasks = allTasks.filter(t => t.id !== data.id);
        renderTasks();
    });
}
```

## 20. public/projects.html (Bonus Page)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projects - Project Manager</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="layout">
        <nav class="sidebar">
            <div class="sidebar-header">
                <h2>Project Manager</h2>
            </div>
            <ul class="nav-menu">
                <li><a href="dashboard.html">📊 Dashboard</a></li>
                <li><a href="projects.html" class="active">📁 Projects</a></li>
                <li><a href="kanban.html">📋 Kanban Board</a></li>
                <li><a href="#" id="logoutBtn">🚪 Logout</a></li>
            </ul>
        </nav>

        <main class="main-content">
            <header class="page-header">
                <h1>Projects</h1>
                <button class="btn btn-primary" onclick="window.location.href='dashboard.html'">+ New Project</button>
            </header>

            <div id="projectsList" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;"></div>
        </main>
    </div>

    <script src="js/app.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', async () => {
            checkAuth();
            await loadProjects();
        });

        document.getElementById('logoutBtn').addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.clear();
            window.location.href = 'index.html';
        });

        async function loadProjects() {
            try {
                const response = await apiCall('/projects');
                const projects = await response.json();
                displayProjects(projects);
            } catch (error) {
                console.error('Error loading projects:', error);
            }
        }

        function displayProjects(projects) {
            const container = document.getElementById('projectsList');
            
            if (projects.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #6b7280;">No projects yet</p>';
                return;
            }

            container.innerHTML = projects.map(project => `
                <div class="stat-card">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                        <h3 style="font-size: 18px; margin: 0;">${project.name}</h3>
                        <span class="task-priority ${getPriorityClass(project.priority)}">${project.priority}</span>
                    </div>
                    <p style="color: #6b7280; font-size: 14px; margin-bottom: 16px;">
                        ${project.description || 'No description'}
                    </p>
                    <div style="margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                            <span>Progress</span>
                            <span style="font-weight: 600;">${project.progress || 0}%</span>
                        </div>
                        <div style="background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="background: #4f46e5; height: 100%; width: ${project.progress || 0}%;"></div>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #6b7280;">
                        <span>📅 ${formatDate(project.startDate)} - ${formatDate(project.endDate)}</span>
                        <span style="text-transform: capitalize;">${project.status}</span>
                    </div>
                    ${project.manager ? `
                        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb; display: flex; align-items: center; gap: 8px;">
                            <img src="${project.manager.avatar}" alt="${project.manager.name}" style="width: 24px; height: 24px; border-radius: 50%;">
                            <span style="font-size: 13px;">Manager: ${project.manager.name}</span>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }
    </script>
</body>
</html>
```

## Setup Instructions

1. **Install dependencies:**
```bash
npm install
```

2. **Setup PostgreSQL database:**
```sql
CREATE DATABASE project_manager;
```

3. **Configure environment variables in `.env`:**
```env
PORT=3000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project_manager
DB_USER=postgres
DB_PASSWORD=your_password
JWT_SECRET=your_secret_key_change_in_production
NODE_ENV=development
```

4. **Start the server:**
```bash
npm start
```

5. **Access the application:**
- Open browser: `http://localhost:3000`
- Register a new account with desired role (admin/manager/employee)
- Start creating projects and assigning tasks

## Key Features Implemented

The application includes **drag-and-drop task management** using the HTML5 Drag and Drop API with event listeners for dragstart, dragover, and drop events. **JWT authentication** is managed securely using localStorage for token storage with automatic redirection on authentication failure. **Real-time updates** are powered by Socket.io, broadcasting task changes to all connected clients instantly. **Dynamic charts** update automatically using Chart.js with the `update()` method when data changes. The **role-based access control** restricts project creation to admin and manager roles, while all users can view and update tasks assigned to them.[1][2][3][4][5][6][7][8][9][10][11][12]

This complete application provides project planning, daily task assignment, visual progress tracking with Kanban boards and charts, real-time collaboration, and a user-friendly interface with drag-and-drop functionality.[5][13][14][1]

[1](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
[2](https://www.w3schools.com/html/html5_draganddrop.asp)
[3](https://blog.bitsrc.io/must-know-javascript-api-drag-and-drop-api-1e3186b83be6)
[4](https://www.descope.com/blog/post/developer-guide-jwt-storage)
[5](https://www.geeksforgeeks.org/javascript/how-to-dynamically-update-values-of-a-chart-in-chartjs/)
[6](https://satvikcoder.hashnode.dev/jwt-token-storage-localstorage-sessionstorage-or-cookies)
[7](https://www.scichart.com/documentation/js/current/Tutorial%2004%20-%20Adding%20Realtime%20Updates.html)
[8](https://codesignal.com/learn/courses/building-a-full-featured-to-do-list-application-1/lessons/real-time-updates-with-socketio)
[9](https://dev.to/novu/sending-real-time-notifications-with-socketio-in-nodejs-1l5j)
[10](https://www.geeksforgeeks.org/node-js/how-to-implement-jwt-authentication-in-express-js-app/)
[11](https://dev.to/hamzakhan/securing-your-expressjs-app-jwt-authentication-step-by-step-aom)
[12](https://www.corbado.com/blog/nodejs-express-postgresql-jwt-authentication-roles)
[13](https://www.youtube.com/watch?v=V2wIK2lBGgk)
[14](https://www.syncfusion.com/javascript-ui-controls/js-kanban-board)
[15](https://reactflow.dev/examples/interaction/drag-and-drop)
[16](https://en.kelen.cc/share/frontend-drag-and-drop-libraries-2025)
[17](https://web.dev/patterns/files/drag-and-drop-directories)
