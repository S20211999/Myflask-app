<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# I want to develop a web application with backend in JavaScript and frontend in html ,css, JavaScript and database to store data i want this tool to plan projects effectively and managers can assign daily task to employees and visually view the progress and evaluate the status of the project i want it to be user-friendly add the extra features to make effective

Here's a comprehensive plan for developing your project management web application with a modern JavaScript stack:

## Recommended Tech Stack

**Backend:** Node.js with Express.js provides the perfect foundation for your JavaScript backend, offering a non-blocking, event-driven architecture ideal for real-time applications. **Frontend:** HTML5, CSS3, and vanilla JavaScript (or React.js for enhanced component reusability). **Database:** PostgreSQL is recommended for task management applications due to its robust ACID compliance, complex query support, and excellent handling of relational data like user-task-project relationships. MongoDB can be considered if you need extreme flexibility in data structure. **Real-time Communication:** Socket.io for instant task updates, notifications, and live progress tracking.[^1_1][^1_2][^1_3][^1_4][^1_5][^1_6]

## Application Architecture

Implement a **3-tier layered architecture** to separate concerns and ensure maintainability:[^1_7][^1_1]

**Controller Layer:** Handles HTTP requests, routing, and user authentication. **Service Layer:** Contains all business logic for task assignment, project planning, and status calculations. **Data Access Layer:** Manages database operations and queries.[^1_2][^1_8]

Structure your project with clear folder organization separating routes, controllers, services, models, and utilities to improve collaboration and code navigation.[^1_8][^1_1]

## Core Features

**User Management:** Role-based access control (Admin, Manager, Employee) with secure JWT authentication. Manager and employee dashboards with different permission levels.

**Project Planning:** Create projects with milestones, deadlines, and budget tracking. Assign project managers and team members. Project templates for recurring workflows.

**Task Management:** Daily task assignment with priority levels (High, Medium, Low). Task dependencies to link related tasks. Subtask support for breaking down complex work. Due dates, time estimates, and actual time tracking. Attachments, comments, and @mentions for collaboration.[^1_9][^1_10]

**Visual Progress Tracking:** **Kanban Board View:** Drag-and-drop interface with customizable columns (To Do, In Progress, Review, Done). **Gantt Chart View:** Timeline visualization with task dependencies and critical path highlighting. **Calendar View:** Monthly/weekly task overview with color-coding by priority. **Dashboard Charts:** Use Chart.js for quick, elegant visualizations - progress bars, pie charts for task distribution, and line graphs for velocity tracking. For advanced custom visualizations, D3.js offers unlimited flexibility.[^1_11][^1_10][^1_12][^1_13][^1_14][^1_15][^1_9]

**Status Evaluation:** Real-time project health indicators (On Track, At Risk, Delayed). Burndown charts showing work remaining vs. time. Completion percentage auto-calculated from task status. Performance metrics per employee (tasks completed, average completion time).[^1_11]

## Enhanced Features for Effectiveness

**Real-time Notifications:** Socket.io-powered instant updates when tasks are assigned, modified, or completed. Browser push notifications for urgent tasks. Daily digest emails summarizing assignments.[^1_4][^1_6]

**Collaboration Tools:** In-app messaging and team chat. File sharing with version control. Activity timeline showing all project changes. @mentions in comments with notifications.[^1_10][^1_9]

**Automation:** Recurring task templates. Automatic task reassignment on employee unavailability. Smart deadline warnings before due dates. Workflow automation (e.g., move to "Review" when marked complete).

**Reporting \& Analytics:** Exportable reports (PDF, Excel) with custom date ranges. Team productivity analytics. Project cost tracking vs. budget. Time-tracking integration for accurate estimates.

**Mobile Responsiveness:** Fully responsive CSS grid/flexbox layout. Touch-optimized interfaces for mobile task updates. Progressive Web App (PWA) capabilities for offline access.

**Integrations:** Calendar sync (Google Calendar, Outlook). Slack/Teams integration for notifications. Third-party time-tracking tools. Export to project management standards (CSV, JSON).

## Database Schema Highlights

Design your PostgreSQL schema with these key tables: Users (id, name, email, role, password_hash), Projects (id, name, description, start_date, end_date, status, manager_id), Tasks (id, project_id, title, description, assigned_to, priority, status, due_date, estimated_hours), Comments, Attachments, and Activity_logs. Use foreign keys and indexes for optimal query performance.[^1_3][^1_5]

## Implementation Best Practices

Follow the **Single Responsibility Principle** - each module should handle one specific functionality. Minimize global variables and encapsulate logic within modules. Implement proper **environment variable management** using dotenv for configuration. Use async/await for clean asynchronous code handling. Apply input validation and sanitization on all user inputs. Implement comprehensive error handling with proper HTTP status codes.[^1_1][^1_2][^1_8]

## User Experience Enhancements

**Intuitive Navigation:** Sidebar with quick access to projects, tasks, calendar, and reports. Breadcrumb navigation for deep project hierarchies. Global search across projects, tasks, and people.

**Drag-and-Drop Interface:** Reorder tasks by priority. Move tasks between project phases. Assign tasks by dragging to employee avatars.

**Keyboard Shortcuts:** Quick task creation (Ctrl+N). Navigate between views (Ctrl+1/2/3). Mark tasks complete (Ctrl+Enter).

**Customization:** Theme selection (light/dark mode). Customizable dashboard widgets. Personalized notification preferences.

This architecture provides a scalable, maintainable foundation for your project management tool while delivering the visual feedback and ease-of-use that managers and employees need for effective collaboration.[^1_2][^1_9][^1_1][^1_11]
<span style="display:none">[^1_16][^1_17][^1_18][^1_19][^1_20]</span>

<div align="center">⁂</div>

[^1_1]: https://blog.logrocket.com/node-js-project-architecture-best-practices/

[^1_2]: https://www.simform.com/blog/node-js-architecture-best-practices/

[^1_3]: https://estuary.dev/blog/postgresql-vs-mongodb/

[^1_4]: https://codesignal.com/learn/courses/building-a-full-featured-to-do-list-application-1/lessons/real-time-updates-with-socketio

[^1_5]: https://www.integrate.io/blog/mongodb-vs-postgresql/

[^1_6]: https://dev.to/novu/sending-real-time-notifications-with-socketio-in-nodejs-1l5j

[^1_7]: https://github.com/goldbergyoni/nodebestpractices

[^1_8]: https://dev.to/shadid12/how-to-architect-a-node-js-project-from-ground-up-1n22

[^1_9]: https://www.octalsoftware.com/blog/task-management-software-development

[^1_10]: https://dhtmlx.com/blog/effective-task-management-dhtmlx-javascript-kanban-list-widgets/

[^1_11]: https://thedigitalprojectmanager.com/tools/project-dashboard-software/

[^1_12]: https://dev.to/okoye_ndidiamaka_5e3b7d30/bringing-data-to-life-how-to-create-interactive-visualizations-with-d3js-and-chartjs-3g4p

[^1_13]: https://www.geeksforgeeks.org/javascript/javascript-libraries-for-data-visualization/

[^1_14]: https://navyuginfo.com/d3-js-chartjs-use/

[^1_15]: https://www.chartjs.org

[^1_16]: https://www.scoutapm.com/blog/nodejs-architecture-and-12-best-practices-for-nodejs-development

[^1_17]: https://webandcrafts.com/blog/nodejs-architecture

[^1_18]: https://www.metricfire.com/blog/top-8-open-source-dashboards/

[^1_19]: https://d3js.org

[^1_20]: https://www.reddit.com/r/d3js/comments/1n3e1a4/moving_beyond_basics_whats_the_best_stack_for/


---

# Yes create and give me code

Here's a complete, production-ready project management web application with all the code you need:

## Project Structure

```
project-manager/
├── server/
│   ├── config/
│   │   └── database.js
│   ├── models/
│   │   ├── User.js
│   │   ├── Project.js
│   │   ├── Task.js
│   │   └── Comment.js
│   ├── middleware/
│   │   └── auth.js
│   ├── routes/
│   │   ├── auth.js
│   │   ├── projects.js
│   │   └── tasks.js
│   └── server.js
├── public/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js
│   │   ├── dashboard.js
│   │   ├── kanban.js
│   │   └── charts.js
│   ├── index.html
│   ├── dashboard.html
│   ├── projects.html
│   └── kanban.html
├── package.json
└── .env
```


## 1. package.json

```json
{
  "name": "project-manager",
  "version": "1.0.0",
  "description": "Project Management Application",
  "main": "server/server.js",
  "scripts": {
    "start": "node server/server.js",
    "dev": "nodemon server/server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "pg": "^8.11.3",
    "pg-hstore": "^2.3.4",
    "sequelize": "^6.35.0",
    "bcryptjs": "^2.4.3",
    "jsonwebtoken": "^9.0.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "socket.io": "^4.6.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.2"
  }
}
```


## 2. .env

```env
PORT=3000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project_manager
DB_USER=postgres
DB_PASSWORD=your_password
JWT_SECRET=your_jwt_secret_key_here_change_in_production
NODE_ENV=development
```


## 3. server/config/database.js

```javascript
const { Sequelize } = require('sequelize');
require('dotenv').config();

const sequelize = new Sequelize(
  process.env.DB_NAME,
  process.env.DB_USER,
  process.env.DB_PASSWORD,
  {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    dialect: 'postgres',
    logging: false,
    pool: {
      max: 5,
      min: 0,
      acquire: 30000,
      idle: 10000
    }
  }
);

module.exports = sequelize;
```


## 4. server/models/User.js

```javascript
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');
const bcrypt = require('bcryptjs');

const User = sequelize.define('User', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      isEmail: true
    }
  },
  password: {
    type: DataTypes.STRING,
    allowNull: false
  },
  role: {
    type: DataTypes.ENUM('admin', 'manager', 'employee'),
    defaultValue: 'employee'
  },
  avatar: {
    type: DataTypes.STRING,
    defaultValue: 'https://ui-avatars.com/api/?name=User'
  },
  isActive: {
    type: DataTypes.BOOLEAN,
    defaultValue: true
  }
}, {
  hooks: {
    beforeCreate: async (user) => {
      if (user.password) {
        user.password = await bcrypt.hash(user.password, 10);
      }
    },
    beforeUpdate: async (user) => {
      if (user.changed('password')) {
        user.password = await bcrypt.hash(user.password, 10);
      }
    }
  }
});

User.prototype.comparePassword = async function(candidatePassword) {
  return await bcrypt.compare(candidatePassword, this.password);
};

module.exports = User;
```


## 5. server/models/Project.js

```javascript
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Project = sequelize.define('Project', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT
  },
  status: {
    type: DataTypes.ENUM('planning', 'active', 'on-hold', 'completed', 'cancelled'),
    defaultValue: 'planning'
  },
  priority: {
    type: DataTypes.ENUM('low', 'medium', 'high', 'critical'),
    defaultValue: 'medium'
  },
  startDate: {
    type: DataTypes.DATE
  },
  endDate: {
    type: DataTypes.DATE
  },
  budget: {
    type: DataTypes.DECIMAL(10, 2),
    defaultValue: 0
  },
  progress: {
    type: DataTypes.INTEGER,
    defaultValue: 0,
    validate: {
      min: 0,
      max: 100
    }
  }
});

module.exports = Project;
```


## 6. server/models/Task.js

```javascript
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Task = sequelize.define('Task', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  title: {
    type: DataTypes.STRING,
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT
  },
  status: {
    type: DataTypes.ENUM('todo', 'in-progress', 'review', 'completed'),
    defaultValue: 'todo'
  },
  priority: {
    type: DataTypes.ENUM('low', 'medium', 'high', 'critical'),
    defaultValue: 'medium'
  },
  dueDate: {
    type: DataTypes.DATE
  },
  estimatedHours: {
    type: DataTypes.DECIMAL(5, 2),
    defaultValue: 0
  },
  actualHours: {
    type: DataTypes.DECIMAL(5, 2),
    defaultValue: 0
  },
  tags: {
    type: DataTypes.ARRAY(DataTypes.STRING),
    defaultValue: []
  }
});

module.exports = Task;
```


## 7. server/models/Comment.js

```javascript
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Comment = sequelize.define('Comment', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  content: {
    type: DataTypes.TEXT,
    allowNull: false
  },
  mentions: {
    type: DataTypes.ARRAY(DataTypes.UUID),
    defaultValue: []
  }
});

module.exports = Comment;
```


## 8. server/middleware/auth.js

```javascript
const jwt = require('jsonwebtoken');
const User = require('../models/User');

const auth = async (req, res, next) => {
  try {
    const token = req.header('Authorization')?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findByPk(decoded.id);

    if (!user || !user.isActive) {
      return res.status(401).json({ error: 'Invalid authentication' });
    }

    req.user = user;
    req.token = token;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid authentication' });
  }
};

const authorize = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Access denied' });
    }
    next();
  };
};

module.exports = { auth, authorize };
```


## 9. server/routes/auth.js

```javascript
const express = require('express');
const jwt = require('jsonwebtoken');
const User = require('../models/User');
const { auth } = require('../middleware/auth');

const router = express.Router();

// Register
router.post('/register', async (req, res) => {
  try {
    const { name, email, password, role } = req.body;

    const existingUser = await User.findOne({ where: { email } });
    if (existingUser) {
      return res.status(400).json({ error: 'Email already registered' });
    }

    const user = await User.create({ name, email, password, role: role || 'employee' });
    const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: '7d' });

    res.status(201).json({
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        avatar: user.avatar
      },
      token
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Login
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    const user = await User.findOne({ where: { email } });
    if (!user || !(await user.comparePassword(password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    if (!user.isActive) {
      return res.status(401).json({ error: 'Account is inactive' });
    }

    const token = jwt.sign({ id: user.id }, process.env.JWT_SECRET, { expiresIn: '7d' });

    res.json({
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        avatar: user.avatar
      },
      token
    });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Get current user
router.get('/me', auth, async (req, res) => {
  res.json({
    id: req.user.id,
    name: req.user.name,
    email: req.user.email,
    role: req.user.role,
    avatar: req.user.avatar
  });
});

// Get all users (for assignment dropdowns)
router.get('/users', auth, async (req, res) => {
  try {
    const users = await User.findAll({
      where: { isActive: true },
      attributes: ['id', 'name', 'email', 'role', 'avatar']
    });
    res.json(users);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

module.exports = router;
```


## 10. server/routes/projects.js

```javascript
const express = require('express');
const Project = require('../models/Project');
const Task = require('../models/Task');
const User = require('../models/User');
const { auth, authorize } = require('../middleware/auth');

const router = express.Router();

// Get all projects
router.get('/', auth, async (req, res) => {
  try {
    const projects = await Project.findAll({
      include: [
        { model: User, as: 'manager', attributes: ['id', 'name', 'email', 'avatar'] },
        { model: Task, as: 'tasks' }
      ],
      order: [['createdAt', 'DESC']]
    });
    res.json(projects);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Get single project
router.get('/:id', auth, async (req, res) => {
  try {
    const project = await Project.findByPk(req.params.id, {
      include: [
        { model: User, as: 'manager', attributes: ['id', 'name', 'email', 'avatar'] },
        {
          model: Task,
          as: 'tasks',
          include: [
            { model: User, as: 'assignedTo', attributes: ['id', 'name', 'avatar'] },
            { model: User, as: 'createdBy', attributes: ['id', 'name'] }
          ]
        }
      ]
    });

    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.json(project);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Create project
router.post('/', auth, authorize('admin', 'manager'), async (req, res) => {
  try {
    const project = await Project.create({
      ...req.body,
      managerId: req.user.id
    });
    res.status(201).json(project);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Update project
router.put('/:id', auth, authorize('admin', 'manager'), async (req, res) => {
  try {
    const project = await Project.findByPk(req.params.id);
    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    await project.update(req.body);
    res.json(project);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Delete project
router.delete('/:id', auth, authorize('admin', 'manager'), async (req, res) => {
  try {
    const project = await Project.findByPk(req.params.id);
    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    await project.destroy();
    res.json({ message: 'Project deleted successfully' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Get project statistics
router.get('/:id/stats', auth, async (req, res) => {
  try {
    const tasks = await Task.findAll({ where: { projectId: req.params.id } });
    
    const stats = {
      total: tasks.length,
      todo: tasks.filter(t => t.status === 'todo').length,
      inProgress: tasks.filter(t => t.status === 'in-progress').length,
      review: tasks.filter(t => t.status === 'review').length,
      completed: tasks.filter(t => t.status === 'completed').length,
      overdue: tasks.filter(t => t.dueDate && new Date(t.dueDate) < new Date() && t.status !== 'completed').length
    };

    res.json(stats);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

module.exports = router;
```


## 11. server/routes/tasks.js

```javascript
const express = require('express');
const Task = require('../models/Task');
const User = require('../models/User');
const Comment = require('../models/Comment');
const { auth } = require('../middleware/auth');

const router = express.Router();

// Get all tasks
router.get('/', auth, async (req, res) => {
  try {
    const { projectId, status, assignedToId } = req.query;
    const where = {};
    
    if (projectId) where.projectId = projectId;
    if (status) where.status = status;
    if (assignedToId) where.assignedToId = assignedToId;

    const tasks = await Task.findAll({
      where,
      include: [
        { model: User, as: 'assignedTo', attributes: ['id', 'name', 'avatar'] },
        { model: User, as: 'createdBy', attributes: ['id', 'name'] }
      ],
      order: [['createdAt', 'DESC']]
    });

    res.json(tasks);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Create task
router.post('/', auth, async (req, res) => {
  try {
    const task = await Task.create({
      ...req.body,
      createdById: req.user.id
    });

    const taskWithRelations = await Task.findByPk(task.id, {
      include: [
        { model: User, as: 'assignedTo', attributes: ['id', 'name', 'avatar'] },
        { model: User, as: 'createdBy', attributes: ['id', 'name'] }
      ]
    });

    // Emit socket event
    req.app.get('io').emit('task:created', taskWithRelations);
    
    res.status(201).json(taskWithRelations);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Update task
router.put('/:id', auth, async (req, res) => {
  try {
    const task = await Task.findByPk(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    await task.update(req.body);
    
    const updatedTask = await Task.findByPk(task.id, {
      include: [
        { model: User, as: 'assignedTo', attributes: ['id', 'name', 'avatar'] },
        { model: User, as: 'createdBy', attributes: ['id', 'name'] }
      ]
    });

    // Emit socket event
    req.app.get('io').emit('task:updated', updatedTask);
    
    res.json(updatedTask);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Delete task
router.delete('/:id', auth, async (req, res) => {
  try {
    const task = await Task.findByPk(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    await task.destroy();
    
    // Emit socket event
    req.app.get('io').emit('task:deleted', { id: req.params.id });
    
    res.json({ message: 'Task deleted successfully' });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// Add comment to task
router.post('/:id/comments', auth, async (req, res) => {
  try {
    const task = await Task.findByPk(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    const comment = await Comment.create({
      ...req.body,
      taskId: req.params.id,
      userId: req.user.id
    });

    const commentWithUser = await Comment.findByPk(comment.id, {
      include: [{ model: User, as: 'user', attributes: ['id', 'name', 'avatar'] }]
    });

    res.status(201).json(commentWithUser);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

module.exports = router;
```


## 12. server/server.js

```javascript
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
require('dotenv').config();

const sequelize = require('./config/database');
const User = require('./models/User');
const Project = require('./models/Project');
const Task = require('./models/Task');
const Comment = require('./models/Comment');

const authRoutes = require('./routes/auth');
const projectRoutes = require('./routes/projects');
const taskRoutes = require('./routes/tasks');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST", "PUT", "DELETE"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Store io instance
app.set('io', io);

// Define relationships
User.hasMany(Project, { foreignKey: 'managerId', as: 'managedProjects' });
Project.belongsTo(User, { foreignKey: 'managerId', as: 'manager' });

Project.hasMany(Task, { foreignKey: 'projectId', as: 'tasks' });
Task.belongsTo(Project, { foreignKey: 'projectId', as: 'project' });

User.hasMany(Task, { foreignKey: 'assignedToId', as: 'assignedTasks' });
Task.belongsTo(User, { foreignKey: 'assignedToId', as: 'assignedTo' });

User.hasMany(Task, { foreignKey: 'createdById', as: 'createdTasks' });
Task.belongsTo(User, { foreignKey: 'createdById', as: 'createdBy' });

Task.hasMany(Comment, { foreignKey: 'taskId', as: 'comments' });
Comment.belongsTo(Task, { foreignKey: 'taskId', as: 'task' });

User.hasMany(Comment, { foreignKey: 'userId', as: 'comments' });
Comment.belongsTo(User, { foreignKey: 'userId', as: 'user' });

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/projects', projectRoutes);
app.use('/api/tasks', taskRoutes);

// Socket.io connection
io.on('connection', (socket) => {
  console.log('New client connected');

  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});

// Serve HTML files
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

// Initialize database and start server
const PORT = process.env.PORT || 3000;

sequelize.sync({ alter: true }).then(() => {
  console.log('Database synchronized');
  server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
}).catch(err => {
  console.error('Unable to connect to database:', err);
});
```


## 13. public/index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager - Login</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body class="login-page">
    <div class="login-container">
        <div class="login-card">
            <h1>Project Manager</h1>
            <p class="subtitle">Manage projects, assign tasks, track progress</p>
            
            <div class="tabs">
                <button class="tab-btn active" data-tab="login">Login</button>
                <button class="tab-btn" data-tab="register">Register</button>
            </div>

            <!-- Login Form -->
            <form id="loginForm" class="auth-form active">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="loginEmail" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="loginPassword" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Login</button>
            </form>

            <!-- Register Form -->
            <form id="registerForm" class="auth-form">
                <div class="form-group">
                    <label>Full Name</label>
                    <input type="text" id="registerName" required>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="registerEmail" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="registerPassword" required>
                </div>
                <div class="form-group">
                    <label>Role</label>
                    <select id="registerRole">
                        <option value="employee">Employee</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Register</button>
            </form>

            <div id="errorMessage" class="error-message"></div>
        </div>
    </div>

    <script src="js/app.js"></script>
</body>
</html>
```


## 14. public/dashboard.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Project Manager</title>
    <link rel="stylesheet" href="css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
</head>
<body>
    <div class="layout">
        <nav class="sidebar">
            <div class="sidebar-header">
                <h2>Project Manager</h2>
            </div>
            <ul class="nav-menu">
                <li><a href="dashboard.html" class="active">📊 Dashboard</a></li>
                <li><a href="projects.html">📁 Projects</a></li>
                <li><a href="kanban.html">📋 Kanban Board</a></li>
                <li><a href="#" id="logoutBtn">🚪 Logout</a></li>
            </ul>
            <div class="user-info">
                <img id="userAvatar" src="" alt="Avatar">
                <div>
                    <div id="userName"></div>
                    <div id="userRole" class="user-role"></div>
                </div>
            </div>
        </nav>

        <main class="main-content">
            <header class="page-header">
                <h1>Dashboard</h1>
                <button class="btn btn-primary" id="createProjectBtn">+ New Project</button>
            </header>

            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Projects</h3>
                    <div class="stat-value" id="totalProjects">0</div>
                </div>
                <div class="stat-card">
                    <h3>Active Tasks</h3>
                    <div class="stat-value" id="activeTasks">0</div>
                </div>
                <div class="stat-card">
                    <h3>Completed</h3>
                    <div class="stat-value" id="completedTasks">0</div>
                </div>
                <div class="stat-card">
                    <h3>Overdue</h3>
                    <div class="stat-value" id="overdueTasks">0</div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="chart-card">
                    <h3>Task Distribution</h3>
                    <canvas id="taskDistChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Project Progress</h3>
                    <canvas id="projectProgressChart"></canvas>
                </div>
            </div>

            <div class="recent-tasks">
                <h3>Recent Tasks</h3>
                <div id="recentTasksList"></div>
            </div>
        </main>
    </div>

    <!-- Create Project Modal -->
    <div id="projectModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>Create New Project</h2>
            <form id="projectForm">
                <div class="form-group">
                    <label>Project Name</label>
                    <input type="text" id="projectName" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="projectDescription" rows="3"></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Start Date</label>
                        <input type="date" id="projectStartDate">
                    </div>
                    <div class="form-group">
                        <label>End Date</label>
                        <input type="date" id="projectEndDate">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Priority</label>
                        <select id="projectPriority">
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Budget</label>
                        <input type="number" id="projectBudget" step="0.01">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Create Project</button>
            </form>
        </div>
    </div>

    <script src="js/dashboard.js"></script>
</body>
</html>
```


## 15. public/kanban.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kanban Board - Project Manager</title>
    <link rel="stylesheet" href="css/style.css">
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
</head>
<body>
    <div class="layout">
        <nav class="sidebar">
            <div class="sidebar-header">
                <h2>Project Manager</h2>
            </div>
            <ul class="nav-menu">
                <li><a href="dashboard.html">📊 Dashboard</a></li>
                <li><a href="projects.html">📁 Projects</a></li>
                <li><a href="kanban.html" class="active">📋 Kanban Board</a></li>
                <li><a href="#" id="logoutBtn">🚪 Logout</a></li>
            </ul>
        </nav>

        <main class="main-content">
            <header class="page-header">
                <h1>Kanban Board</h1>
                <div class="header-actions">
                    <select id="projectFilter" class="form-control">
                        <option value="">All Projects</option>
                    </select>
                    <button class="btn btn-primary" id="createTaskBtn">+ New Task</button>
                </div>
            </header>

            <div class="kanban-board">
                <div class="kanban-column" data-status="todo">
                    <div class="column-header">
                        <h3>To Do</h3>
                        <span class="task-count" id="todoCount">0</span>
                    </div>
                    <div class="task-list" id="todoList"></div>
                </div>

                <div class="kanban-column" data-status="in-progress">
                    <div class="column-header">
                        <h3>In Progress</h3>
                        <span class="task-count" id="inProgressCount">0</span>
                    </div>
                    <div class="task-list" id="inProgressList"></div>
                </div>

                <div class="kanban-column" data-status="review">
                    <div class="column-header">
                        <h3>Review</h3>
                        <span class="task-count" id="reviewCount">0</span>
                    </div>
                    <div class="task-list" id="reviewList"></div>
                </div>

                <div class="kanban-column" data-status="completed">
                    <div class="column-header">
                        <h3>Completed</h3>
                        <span class="task-count" id="completedCount">0</span>
                    </div>
                    <div class="task-list" id="completedList"></div>
                </div>
            </div>
        </main>
    </div>

    <!-- Create Task Modal -->
    <div id="taskModal" class="modal">
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2 id="taskModalTitle">Create New Task</h2>
            <form id="taskForm">
                <input type="hidden" id="taskId">
                <div class="form-group">
                    <label>Project</label>
                    <select id="taskProject" required></select>
                </div>
                <div class="form-group">
                    <label>Task Title</label>
                    <input type="text" id="taskTitle" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="taskDescription" rows="3"></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Assign To</label>
                        <select id="taskAssignee"></select>
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select id="taskPriority">
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Due Date</label>
                        <input type="date" id="taskDueDate">
                    </div>
                    <div class="form-group">
                        <label>Estimated Hours</label>
                        <input type="number" id="taskEstimatedHours" step="0.5" min="0">
                    </div>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Save Task</button>
            </form>
        </div>
    </div>

    <script src="js/kanban.js"></script>
</body>
</html>
```


## 16. public/css/style.css

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #4f46e5;
    --primary-dark: #4338ca;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: var(--gray-50);
    color: var(--gray-800);
    line-height: 1.6;
}

/* Login Page */
.login-page {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: linear-gradient(135deg, var(--primary) 0%, #7c3aed 100%);
}

.login-container {
    width: 100%;
    max-width: 450px;
    padding: 20px;
}

.login-card {
    background: white;
    border-radius: 12px;
    padding: 40px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.login-card h1 {
    font-size: 2rem;
    color: var(--gray-900);
    margin-bottom: 8px;
}

.subtitle {
    color: var(--gray-600);
    margin-bottom: 30px;
}

.tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 30px;
    border-bottom: 2px solid var(--gray-200);
}

.tab-btn {
    flex: 1;
    padding: 12px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    color: var(--gray-600);
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.tab-btn.active {
    color: var(--primary);
    border-bottom-color: var(--primary);
}

.auth-form {
    display: none;
}

.auth-form.active {
    display: block;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 6px;
    font-weight: 500;
    color: var(--gray-700);
}

.form-group input,
.form-group select,
.form-group textarea {
    width: 100%;
    padding: 12px;
    border: 2px solid var(--gray-200);
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.3s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: none;
    border-color: var(--primary);
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-block {
    width: 100%;
}

.error-message {
    margin-top: 15px;
    padding: 12px;
    background: #fef2f2;
    color: var(--danger);
    border-radius: 8px;
    display: none;
}

/* Layout */
.layout {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 260px;
    background: var(--gray-900);
    color: white;
    display: flex;
    flex-direction: column;
    position: fixed;
    height: 100vh;
}

.sidebar-header {
    padding: 24px 20px;
    border-bottom: 1px solid var(--gray-800);
}

.sidebar-header h2 {
    font-size: 1.5rem;
}

.nav-menu {
    flex: 1;
    list-style: none;
    padding: 20px 0;
}

.nav-menu li a {
    display: block;
    padding: 12px 20px;
    color: var(--gray-300);
    text-decoration: none;
    transition: all 0.3s;
}

.nav-menu li a:hover,
.nav-menu li a.active {
    background: var(--gray-800);
    color: white;
}

.user-info {
    padding: 20px;
    border-top: 1px solid var(--gray-800);
    display: flex;
    align-items: center;
    gap: 12px;
}

.user-info img {
    width: 40px;
    height: 40px;
    border-radius: 50%;
}

.user-role {
    font-size: 12px;
    color: var(--gray-400);
    text-transform: capitalize;
}

.main-content {
    flex: 1;
    margin-left: 260px;
    padding: 30px;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
}

.page-header h1 {
    font-size: 2rem;
    color: var(--gray-900);
}

.header-actions {
    display: flex;
    gap: 15px;
    align-items: center;
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-card h3 {
    font-size: 14px;
    color: var(--gray-600);
    margin-bottom: 8px;
}

.stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary);
}

/* Charts */
.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.chart-card {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-card h3 {
    margin-bottom: 20px;
    color: var(--gray-700);
}

/* Kanban Board */
.kanban-board {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    overflow-x: auto;
}

.kanban-column {
    background: var(--gray-100);
    border-radius: 12px;
    padding: 16px;
    min-width: 280px;
}

.column-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--gray-200);
}

.column-header h3 {
    font-size: 1rem;
    color: var(--gray-700);
}

.task-count {
    background: var(--gray-300);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
}

.task-list {
    min-height: 400px;
}

.task-card {
    background: white;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    cursor: grab;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: all 0.3s;
}

.task-card:hover {
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
}

.task-card.dragging {
    opacity: 0.5;
}

.task-priority {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 8px;
}

.priority-low {
    background: #dbeafe;
    color: #1e40af;
}

.priority-medium {
    background: #fef3c7;
    color: #92400e;
}

.priority-high {
    background: #fed7aa;
    color: #9a3412;
}

.priority-critical {
    background: #fee2e2;
    color: #991b1b;
}

.task-title {
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--gray-900);
}

.task-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--gray-200);
    font-size: 12px;
    color: var(--gray-600);
}

.task-assignee {
    display: flex;
    align-items: center;
    gap: 6px;
}

.task-assignee img {
    width: 24px;
    height: 24px;
    border-radius: 50%;
}

/* Modal */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
}

.modal.active {
    display: flex;
    justify-content: center;
    align-items: center;
}

.modal-content {
    background: white;
    border-radius: 12px;
    padding: 30px;
    width: 90%;
    max-width: 600px;
    max-height: 90vh;
    overflow-y: auto;
}

.close {
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
    color: var(--gray-600);
}

.close:hover {
    color: var(--gray-900);
}

/* Recent Tasks */
.recent-tasks {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.recent-tasks h3 {
    margin-bottom: 20px;
    color: var(--gray-700);
}

@media (max-width: 768px) {
    .sidebar {
        width: 200px;
    }
    
    .main-content {
        margin-left: 200px;
    }
    
    .kanban-board {
        grid-template-columns: 1fr;
    }
}
```

Due to length constraints, I'll provide the remaining JavaScript files in a follow-up. The key files are:

- **js/app.js** - Handles authentication
- **js/dashboard.js** - Dashboard functionality with Chart.js
- **js/kanban.js** - Drag-and-drop Kanban board with Socket.io


## Installation \& Setup

1. Install PostgreSQL on your system
2. Create database: `CREATE DATABASE project_manager;`
3. Run: `npm install`
4. Configure `.env` with your database credentials
5. Start server: `npm start`
6. Open browser: `http://localhost:3000`

The application includes JWT authentication, role-based access control, real-time updates via Socket.io, PostgreSQL with Sequelize ORM, Chart.js visualizations, drag-and-drop Kanban board, and complete CRUD operations for projects and tasks.[^2_1][^2_2][^2_3][^2_4][^2_5][^2_6]

Would you like me to provide the remaining JavaScript files (app.js, dashboard.js, kanban.js)?
<span style="display:none">[^2_10][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://www.geeksforgeeks.org/node-js/how-to-implement-jwt-authentication-in-express-js-app/

[^2_2]: https://dev.to/hamzakhan/securing-your-expressjs-app-jwt-authentication-step-by-step-aom

[^2_3]: https://www.corbado.com/blog/nodejs-express-postgresql-jwt-authentication-roles

[^2_4]: https://webprogrammingtoolsandframeworks.sdds.ca/Relational-Database-Postgres/sequelize-orm-with-postgres

[^2_5]: https://www.youtube.com/watch?v=V2wIK2lBGgk

[^2_6]: https://www.robinwieruch.de/postgres-express-setup-tutorial/

[^2_7]: https://www.topcoder.com/thrive/articles/authentication-and-authorization-in-express-js-api-using-jwt

[^2_8]: https://www.sevensquaretech.com/nodejs-jwt-authentication-mysql-with-code/

[^2_9]: https://blog.devgenius.io/node-js-jwt-authentication-with-express-and-mongodb-ecce331c1190

[^2_10]: https://www.syncfusion.com/javascript-ui-controls/js-kanban-board


---

# Yes

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

    taskDistChart.data.datasets[^3_0].data = [
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
    projectProgressChart.data.datasets[^3_0].data = projectProgress;
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
    document.getElementById('taskDueDate').value = task.dueDate ? task.dueDate.split('T')[^3_0] : '';
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

The application includes **drag-and-drop task management** using the HTML5 Drag and Drop API with event listeners for dragstart, dragover, and drop events. **JWT authentication** is managed securely using localStorage for token storage with automatic redirection on authentication failure. **Real-time updates** are powered by Socket.io, broadcasting task changes to all connected clients instantly. **Dynamic charts** update automatically using Chart.js with the `update()` method when data changes. The **role-based access control** restricts project creation to admin and manager roles, while all users can view and update tasks assigned to them.[^3_1][^3_2][^3_3][^3_4][^3_5][^3_6][^3_7][^3_8][^3_9][^3_10][^3_11][^3_12]

This complete application provides project planning, daily task assignment, visual progress tracking with Kanban boards and charts, real-time collaboration, and a user-friendly interface with drag-and-drop functionality.[^3_5][^3_13][^3_14][^3_1]
<span style="display:none">[^3_15][^3_16][^3_17]</span>

<div align="center">⁂</div>

[^3_1]: https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API

[^3_2]: https://www.w3schools.com/html/html5_draganddrop.asp

[^3_3]: https://blog.bitsrc.io/must-know-javascript-api-drag-and-drop-api-1e3186b83be6

[^3_4]: https://www.descope.com/blog/post/developer-guide-jwt-storage

[^3_5]: https://www.geeksforgeeks.org/javascript/how-to-dynamically-update-values-of-a-chart-in-chartjs/

[^3_6]: https://satvikcoder.hashnode.dev/jwt-token-storage-localstorage-sessionstorage-or-cookies

[^3_7]: https://www.scichart.com/documentation/js/current/Tutorial 04 - Adding Realtime Updates.html

[^3_8]: https://codesignal.com/learn/courses/building-a-full-featured-to-do-list-application-1/lessons/real-time-updates-with-socketio

[^3_9]: https://dev.to/novu/sending-real-time-notifications-with-socketio-in-nodejs-1l5j

[^3_10]: https://www.geeksforgeeks.org/node-js/how-to-implement-jwt-authentication-in-express-js-app/

[^3_11]: https://dev.to/hamzakhan/securing-your-expressjs-app-jwt-authentication-step-by-step-aom

[^3_12]: https://www.corbado.com/blog/nodejs-express-postgresql-jwt-authentication-roles

[^3_13]: https://www.youtube.com/watch?v=V2wIK2lBGgk

[^3_14]: https://www.syncfusion.com/javascript-ui-controls/js-kanban-board

[^3_15]: https://reactflow.dev/examples/interaction/drag-and-drop

[^3_16]: https://en.kelen.cc/share/frontend-drag-and-drop-libraries-2025

[^3_17]: https://web.dev/patterns/files/drag-and-drop-directories

