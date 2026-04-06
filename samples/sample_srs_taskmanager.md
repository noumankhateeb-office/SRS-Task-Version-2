# Software Requirements Specification (SRS) for Task Management Application

---

### 1. Introduction

### 1.1 Purpose

This document describes the Software Requirements Specification (SRS) for a Task Management Application, a web-based tool for creating, organizing, and tracking tasks and projects for teams and individuals.

### 1.2 Scope

The Task Management Application will provide task creation, assignment, status tracking, project organization, and team collaboration features. The platform is built using **React**, **Express**, and **PostgreSQL**.

### 1.3 Definitions, Acronyms, and Abbreviations

- **User**: Any registered user of the application.
- **Admin**: A user with administrative privileges.
- **Manager**: A user who can create projects and assign tasks.
- **System**: The Task Management Application being developed.

---

### 2. Overall Description

### 2.1 Product Perspective

The Task Management Application is a standalone web-based productivity tool that helps teams organize work into projects and tasks with clear ownership and deadlines.

### 2.2 Product Features

- **Task Management**: Users can create, edit, delete, and track tasks.
- **Project Organization**: Tasks can be grouped into projects.
- **Team Collaboration**: Users can comment on tasks and mention teammates.
- **Dashboard**: Overview of assigned tasks, deadlines, and progress.
- **Notifications**: Real-time alerts for task assignments and updates.

### 2.3 User Classes and Characteristics

- **User**: Standard user who creates and completes tasks.
- **Manager**: Creates projects, assigns tasks, and monitors progress.
- **Admin**: Full system access including user management.

### 2.4 Operating Environment

- **Frontend**: React single-page application accessible via modern browsers.
- **Backend**: Node.js with Express framework, PostgreSQL database with Sequelize ORM.

### 2.5 Constraints

- No desktop or mobile native application will be developed.
- Integration with external project management tools (Jira, Trello) is out of scope.
- File attachments are limited to 10MB per file.

---

### 3. System Features and Requirements

### 3.1 Functional Requirements

### FR-01: Task Creation

- **Requirements**:
    - Form with title, description, priority, and due date fields.
    - Title is required and must be under 100 characters.
    - Priority options: Low, Medium, High, Critical.
    - Due date must be in the future.
    - Tasks can be assigned to one or more team members.
- **Acceptance Criteria**:
    - Task is created successfully with all required fields.
    - System rejects task without title.
    - Priority is set correctly.
    - Past due dates are rejected.
    - Assigned users receive notification.

### FR-02: Task Board View

- **Requirements**:
    - Kanban-style board with columns: To Do, In Progress, In Review, Done.
    - Users can drag and drop tasks between columns.
    - Board shows task title, assignee avatar, priority indicator, and due date.
    - Tasks can be filtered by assignee, priority, and due date.
- **Acceptance Criteria**:
    - Board displays all project tasks in correct columns.
    - Drag and drop updates task status in database.
    - Filters correctly narrow down visible tasks.
    - Board updates in real-time when other users make changes.

### FR-03: Task Comments

- **Requirements**:
    - Users can add comments to tasks.
    - Comments support text and @mentions of team members.
    - Mentioned users receive a notification.
    - Comments are displayed in chronological order.
- **Acceptance Criteria**:
    - Comment is added and displayed immediately.
    - @mention triggers notification to mentioned user.
    - Comments show author name, avatar, and timestamp.
    - Users can edit and delete their own comments.

### FR-04: Project Dashboard

- **Requirements**:
    - Dashboard shows summary of all user's projects.
    - Each project shows task count by status, overdue tasks, and progress percentage.
    - Recent activity feed showing latest task updates.
    - Quick actions to create task or view project.
- **Acceptance Criteria**:
    - Dashboard loads with correct project summaries.
    - Progress percentage matches actual task completion.
    - Activity feed shows latest 20 activities.
    - Quick actions navigate to correct pages.

---

### 3.2 Non-Functional Requirements

### NFR-01: Performance

- **Requirements**:
    - Dashboard shall load in under 3 seconds.
    - Drag and drop on task board shall have less than 200ms latency.
    - System shall support 500 concurrent users.

### NFR-02: Usability

- **Requirements**:
    - Application shall be accessible on screens from 768px width and above.
    - Color scheme shall meet WCAG 2.1 AA contrast requirements.
    - Keyboard navigation support for all major features.

---

### 4. External Interface Requirements

### 4.1 User Interface

- Modern, clean interface with responsive design. Support for light and dark themes.

### 4.2 Software Interfaces

- PostgreSQL database via Sequelize ORM.
- Email service for sending notifications.

---

### 5. System Attributes

### 5.1 Reliability

- System uptime target of 99.5%.
- Automatic data backup every 24 hours.

### 5.2 Scalability

- Architecture shall support horizontal scaling of API servers.
- Database read replicas for improved query performance.

### 5.3 Security

- Role-based access control (User, Manager, Admin).
- All API endpoints require authentication.
- XSS and CSRF protection on all forms.

### 5.4 Maintainability

- RESTful API design following OpenAPI specification.
- Comprehensive API documentation.
- Unit test coverage above 80%.

---

### 6. Out of Scope

- Native mobile applications (iOS/Android).
- Integration with Jira, Trello, or Asana.
- Gantt chart or timeline view.
- Time tracking features.
