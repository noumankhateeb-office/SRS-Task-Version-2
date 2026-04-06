# Software Requirements Specification (SRS) for Field Service Management Platform

---

### 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the requirements for a **Field Service Management Platform** used by service teams handling on-site installation, maintenance, and repair work. The platform will support ticket intake, technician scheduling, mobile work orders, parts usage, customer signatures, and service performance reporting.

### 1.2 Scope

The platform will replace manual dispatch boards and spreadsheet-based service tracking with a centralized web system. The application will use **React**, **Node.js**, **PostgreSQL**, and **REST APIs** and will support office operations and dispatcher workflows in the first release.

### 1.3 Definitions, Acronyms, and Abbreviations

- **Dispatcher**: User responsible for assigning technicians and scheduling work orders.
- **Technician**: Field staff member performing customer service visits.
- **Work Order**: A service job assigned to a technician.
- **SLA**: Service Level Agreement defining response and resolution targets.

---

### 2. Overall Description

### 2.1 Product Perspective

The system will coordinate the operational flow between customer service, dispatchers, field technicians, and supervisors. It will centralize the lifecycle of a service request from creation to completion.

### 2.2 Product Features

- Service ticket creation and classification
- Technician scheduling and dispatch management
- Work order execution and completion tracking
- Parts and inventory usage capture
- Customer confirmation and service history
- SLA and operational performance reporting

### 2.3 User Classes and Characteristics

- **Dispatcher**: Assigns work orders based on priority, location, and technician availability.
- **Technician**: Views assigned jobs and records service activity.
- **Supervisor**: Monitors service backlogs, SLA breaches, and team performance.

### 2.4 Operating Environment

- **Frontend**: Web-based dispatcher and supervisor interface for desktop browsers.
- **Backend**: Node.js services connected to PostgreSQL and messaging-based notifications.
- **Deployment**: Cloud-hosted deployment with audit logging and scheduled backups.

### 2.5 Constraints

- Offline mobile technician support is not in scope for the first version.
- GPS route optimization will be added in a later phase.
- All customer-facing job records must be retained for service history review.

---

### 3. System Features and Requirements

### 3.1 Functional Requirements (FR)

**FR-01: Service Ticket Intake**

- Customer service users must be able to create tickets with customer details, location, service category, issue summary, and priority.
- Ticket categories must support configurable severity and response targets.
- Duplicate ticket checks should warn users when a similar open ticket already exists for the same customer and asset.

**FR-02: Technician Scheduling**

- Dispatchers must be able to assign tickets to technicians based on skill, region, and availability.
- The schedule view must display technician workload by day and time slot.
- Reassignment history must be logged whenever a work order changes ownership.

**FR-03: Work Order Execution**

- Technicians must be able to record arrival time, work performed, parts used, and completion notes against a work order.
- Work orders must support statuses such as assigned, in progress, on hold, completed, and follow-up required.
- Supervisors must be able to review incomplete work orders and reopen completed jobs when necessary.

**FR-04: Parts Usage and Inventory Consumption**

- Technicians must be able to record spare parts consumed during a job.
- The system must reduce available stock when parts are issued or consumed.
- Inventory exceptions must be visible when requested parts are not available in the assigned service location.

**FR-05: Customer Confirmation**

- Completed work orders must support customer sign-off with name, timestamp, and service confirmation.
- Customers should receive a service summary by email after job completion.
- Supervisors must be able to review disputed or unsigned work orders separately.

**FR-06: SLA Monitoring**

- The platform must track response and resolution times against the SLA applicable to each ticket.
- Supervisors must be able to view open SLA breaches and jobs at risk of breaching within dashboard views.
- Reports must support filtering by customer, service team, technician, and time period.

**FR-07: Service Performance Dashboard**

- The system must provide dashboards showing ticket volume, first-time fix rate, technician utilization, and recurring issue trends.
- Dashboard metrics must be traceable to underlying work orders and service events.

---

### 4. External Interface Requirements

### 4.1 User Interface

- The interface must prioritize dispatcher productivity with quick filtering, assignment, and queue views.

### 4.2 Software Interfaces

- The platform must integrate with email services for service updates and completion summaries.
- Import and export support must be available for customer assets and service history data.

---

### 5. System Attributes

### 5.1 Maintainability

- Scheduling, work order, and reporting modules should be independently maintainable.

### 5.2 Security

- Customer details and asset history must be protected by role-based access controls and encryption.

---

### 6. Out of Scope

- Technician-native mobile application in the first release.
- Live GPS tracking and route optimization.
