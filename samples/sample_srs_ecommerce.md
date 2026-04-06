# Software Requirements Specification (SRS) for E-Commerce Platform

---

### 1. Introduction

### 1.1 Purpose

This document describes the Software Requirements Specification (SRS) for an E-Commerce platform, a web-based shopping platform for buying and selling products online.

### 1.2 Scope

The E-Commerce platform will provide user registration and authentication, product browsing, shopping cart, checkout, and order management and tracking features. The platform is built using **Next.js**, **Prisma**, and **MongoDB**.

### 1.3 Definitions, Acronyms, and Abbreviations

- **Customer**: A user who browses and purchases products.
- **Admin**: A user with administrative privileges for managing the platform.
- **System**: The E-Commerce platform being developed.
- **API**: Application Programming Interface.

---

### 2. Overall Description

### 2.1 Product Perspective

The E-Commerce platform will be a standalone web-based application, providing essential features for customers to purchase products online and for admins to manage product listings, orders, and user accounts.

### 2.2 Product Features

- **User Authentication**: Users can register, log in, and log out of the platform.
- **Product Catalog**: Users can browse and search for products.
- **Shopping Cart**: Customers can add products to their cart and proceed to checkout.
- **Order Management**: Admins can manage orders and view order history.

### 2.3 User Classes and Characteristics

- **Customer**: End-users who interact with the product catalog, shopping cart, and checkout.
- **Admin**: Users with the ability to manage products, orders, and users.

### 2.4 Operating Environment

- **Frontend**: Web-based application accessible via modern browsers (Chrome, Firefox, Safari).
- **Backend**: Node.js with Next.js framework, Prisma ORM for database interactions, and MongoDB for data storage.

### 2.5 Constraints

- No mobile application development is included in the scope.
- Integration with third-party marketplaces and cryptocurrency payment support is out of scope.

---

### 3. System Features and Requirements

### 3.1 Functional Requirements

### FR-01: User Login

- **Requirements**:
    - Two input fields for email and password.
    - The email must be validated for the correct format.
    - The password field should have a show/hide toggle.
- **Acceptance Criteria**:
    - User can successfully log in with a valid email and password.
    - The system shows an error message for invalid credentials.
    - User is redirected to the dashboard after successful login.

### FR-02: User Registration

- **Requirements**:
    - Registration form with name, email, and password fields.
    - Password must be at least 8 characters with one uppercase and one number.
    - System shall send verification email after registration.
    - Duplicate email addresses shall not be allowed.
- **Acceptance Criteria**:
    - User can register with valid details and receive confirmation.
    - System rejects registration with existing email.
    - Verification email is received within 60 seconds.
    - User cannot login until email is verified.

### FR-03: Product Catalog

- **Requirements**:
    - Display all products with name, image, price, and category.
    - Users can filter products by category and price range.
    - Users can sort products by price, name, and newest.
    - Pagination with 20 products per page.
- **Acceptance Criteria**:
    - All active products are displayed with correct details.
    - Filters correctly narrow down product list.
    - Sort order changes immediately on selection.
    - Pagination navigation works correctly.

### FR-04: Shopping Cart

- **Requirements**:
    - Users can add products to cart with quantity selection.
    - Users can update item quantities in cart.
    - Users can remove items from cart.
    - Cart displays subtotal, tax, and grand total.
    - Cart persists across sessions for logged-in users.
- **Acceptance Criteria**:
    - Product is added to cart with correct quantity.
    - Quantity update reflects in cart total immediately.
    - Item removal updates cart total correctly.
    - Cart contents persist after logout and login.

### FR-05: Order Placement

- **Requirements**:
    - Users can place orders from cart with delivery address.
    - System validates stock availability before order confirmation.
    - Order confirmation page shows order summary.
    - System generates unique order ID.
- **Acceptance Criteria**:
    - Order is placed successfully with all cart items.
    - Out-of-stock items prevent order placement.
    - Order confirmation shows correct details and order ID.
    - User receives order confirmation email.

---

### 3.2 Non-Functional Requirements

### NFR-01: Performance

- **Requirements**:
    - The system shall load pages in under 2 seconds.
    - API response time shall be under 500ms.

### NFR-02: Security

- **Requirements**:
    - All passwords must be hashed using bcrypt.
    - SSL encryption for all client-server communication.
    - JWT tokens for authentication with 24-hour expiry.

---

### 4. External Interface Requirements

### 4.1 User Interface

- Web-based interface with responsive design for both desktop and mobile screen sizes.

### 4.2 Hardware Interfaces

- No specific hardware requirements; the system will be deployed on cloud infrastructure.

### 4.3 Software Interfaces

- The backend will interact with MongoDB via Prisma ORM for data storage.

### 4.4 Communication Interfaces

- The system will communicate with email servers to send confirmation emails.

---

### 5. System Attributes

### 5.1 Reliability

- The system should be available 99.9% of the time.

### 5.2 Scalability

- The platform should be able to scale horizontally to support increased traffic during peak seasons.

### 5.3 Security

- All passwords should be hashed and stored securely.
- SSL encryption must be used for all communications between the client and server.

### 5.4 Maintainability

- The platform should have a modular architecture, making it easy to add new features or update existing ones.

---

### 6. Out of Scope

- Mobile application development.
- Third-party marketplace integration.
- Cryptocurrency payment support.
