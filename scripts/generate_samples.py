"""
Generate diverse SRS training samples with 30-50 FRs each.
Each sample covers a unique domain with realistic requirements.
"""
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.srs_to_json import parse_srs

DATASET_ROOT = PROJECT_ROOT / "data"
TRAINING_DIR = DATASET_ROOT / "training"
EVALUATION_DIR = DATASET_ROOT / "evaluation"

# ── Domain definitions with FR pools ──────────────────────────────
DOMAINS = [
    {
        "file": "23_travel_booking.json",
        "title": "Travel Booking Platform",
        "tech": ["React", "Node.js", "PostgreSQL", "Redis", "Elasticsearch"],
        "frs": [
            ("Flight Search", ["Search flights by origin, destination, dates, passengers", "Filter by airline, stops, departure time, price range", "Sort by price, duration, departure time", "Show baggage and cancellation policy per result"], ["Search returns matching flights", "Filters narrow results correctly", "Sort order updates immediately", "Policy info displays accurately"]),
            ("Hotel Search", ["Search hotels by destination and dates", "Filter by star rating, amenities, price", "Map view with hotel markers", "Compare hotel prices across providers"], ["Hotels match search criteria", "Filters work correctly", "Map shows accurate locations", "Comparison displays side by side"]),
            ("Flight Booking", ["Select flight and enter passenger details", "Seat selection with seat map", "Add baggage and meal preferences", "Payment processing with multiple methods"], ["Booking created with passenger info", "Seat assigned on map", "Add-ons reflected in price", "Payment processed successfully"]),
            ("Hotel Reservation", ["Select room type and dates", "Guest details and special requests", "Cancellation policy display", "Booking confirmation with details"], ["Room reserved for dates", "Guest info saved", "Policy shown before booking", "Confirmation sent via email"]),
            ("Trip Itinerary Builder", ["Auto-generate itinerary from bookings", "Add custom activities and notes", "Day-by-day schedule view", "Share itinerary with travel companions"], ["Itinerary includes all bookings", "Custom items added correctly", "Schedule organized by day", "Shared link accessible"]),
            ("Car Rental", ["Search available vehicles by location and dates", "Filter by vehicle type, transmission, and price", "Add insurance and extras", "Pickup and dropoff location selection"], ["Available vehicles shown", "Filters work correctly", "Extras added to price", "Locations selectable on map"]),
            ("Travel Insurance", ["Compare insurance plans for trip", "Coverage details and exclusions", "Purchase insurance with trip link", "Claims submission process"], ["Plans displayed with comparison", "Details clearly shown", "Purchase links to booking", "Claim form submitted"]),
            ("Visa and Document Checklist", ["Visa requirements by nationality and destination", "Document checklist generation", "Upload and track documents", "Visa application status tracking"], ["Requirements shown correctly", "Checklist generated automatically", "Documents uploaded securely", "Status updates tracked"]),
            ("Currency Converter", ["Real-time exchange rate display", "Multi-currency conversion", "Rate alerts for favorable rates", "Historical rate charts"], ["Rates accurate and current", "Multiple currencies convertible", "Alerts trigger at target rate", "Charts show historical data"]),
            ("Travel Reviews", ["Rate and review destinations", "Photo upload with reviews", "Helpful vote system", "Review moderation"], ["Review submitted successfully", "Photos display with review", "Vote counts update", "Inappropriate reviews flagged"]),
            ("Loyalty Program", ["Earn points on bookings", "Redeem points for discounts", "Tier levels with perks", "Points transfer between members"], ["Points calculated correctly", "Redemption deducts from total", "Tier benefits applied", "Transfer processes correctly"]),
            ("Group Booking", ["Book for multiple travelers", "Group discount calculation", "Shared payment splitting", "Group itinerary coordination"], ["Multiple passengers booked", "Discount applies correctly", "Payment split among members", "Group sees shared itinerary"]),
            ("Airport Transfer", ["Book airport pickup and dropoff", "Vehicle selection by group size", "Flight tracking for pickup timing", "Driver contact and tracking"], ["Transfer booked for flight", "Vehicle fits group", "Pickup adjusts to flight delay", "Driver location trackable"]),
            ("Travel Alerts", ["Destination safety alerts", "Weather advisories", "Flight status notifications", "Price drop alerts for saved searches"], ["Safety info accurate", "Weather displayed for dates", "Flight delays notified", "Price drops trigger alert"]),
            ("Multi-city Trip Planning", ["Plan trips with multiple destinations", "Optimize route between cities", "Inter-city transport options", "Combined pricing for segments"], ["Multiple cities added to trip", "Route optimization suggests order", "Transport options shown", "Combined price calculated"]),
            ("Travel Blog and Guides", ["Destination guides with attractions", "User-generated travel stories", "Local tips and recommendations", "Seasonal travel suggestions"], ["Guides display correct info", "Stories published and visible", "Tips shown by location", "Seasonal suggestions relevant"]),
            ("Booking Calendar", ["Visual calendar showing all bookings", "Sync with personal calendar", "Overlap detection", "Quick view booking details"], ["Calendar shows all trips", "Sync exports correctly", "Overlaps highlighted", "Details shown on click"]),
            ("Travel Expense Tracking", ["Log travel expenses by category", "Receipt scanning and upload", "Budget vs actual comparison", "Export expense report"], ["Expenses logged correctly", "Receipts scanned accurately", "Budget comparison accurate", "Report exports as PDF"]),
            ("Customer Support", ["Live chat for booking issues", "Call back scheduling", "FAQ and help center", "Complaint tracking with resolution"], ["Chat connects to agent", "Callback received on time", "FAQ searchable", "Complaint tracked to resolution"]),
            ("Partner Portal for Hotels", ["Hotel managers update availability", "Rate management with seasonal pricing", "Booking management dashboard", "Revenue and occupancy reports"], ["Availability updates in real-time", "Rates apply per season", "Bookings manageable", "Reports accurate"]),
            ("Recommendation Engine", ["Personalized destination suggestions", "Based on travel history and preferences", "Trending destinations", "Similar traveler recommendations"], ["Suggestions match preferences", "History influences recommendations", "Trending data current", "Similar traveler logic sound"]),
            ("Package Deals", ["Pre-built flight+hotel packages", "Customizable package builder", "Package discount calculation", "Compare package vs individual booking"], ["Packages display correctly", "Customization works", "Discount calculated", "Comparison shows savings"]),
            ("Offline Access", ["Download booking details offline", "Offline maps for destinations", "Offline itinerary access", "Sync when back online"], ["Details available offline", "Maps load without internet", "Itinerary accessible", "Changes sync on reconnect"]),
            ("Accessibility Features", ["Screen reader support", "High contrast mode", "Keyboard navigation", "Alt text for all images"], ["Screen reader describes content", "High contrast renders correctly", "Full keyboard navigation", "Alt text present on images"]),
            ("Admin Analytics", ["Booking volume metrics", "Revenue tracking by segment", "Conversion funnel analysis", "Customer lifetime value reports"], ["Metrics match actual bookings", "Revenue segmented correctly", "Funnel shows drop-offs", "CLV calculated accurately"]),
            ("Refund Processing", ["Cancel booking with refund calculation", "Partial cancellation support", "Refund to original payment method", "Refund status tracking"], ["Refund calculated per policy", "Partial cancel adjusts correctly", "Refund reaches original method", "Status trackable by user"]),
            ("Multi-language Support", ["UI available in 10+ languages", "Content localization for destinations", "Currency display by locale", "RTL language support"], ["Language switch works seamlessly", "Content translated accurately", "Currency matches locale", "RTL renders correctly"]),
            ("Notification System", ["Booking confirmation notifications", "Check-in reminders", "Price change alerts", "Promotional offer notifications"], ["Confirmations sent immediately", "Reminders timed correctly", "Price alerts accurate", "Offers reach opted-in users"]),
            ("API Gateway for Partners", ["REST API for OTA integrations", "Webhook for booking events", "Rate limiting and authentication", "API usage analytics"], ["API returns correct data", "Webhooks fire on events", "Rate limits enforced", "Usage analytics tracked"]),
            ("Data Privacy and GDPR", ["User data export request", "Account deletion with data purge", "Cookie consent management", "Privacy settings dashboard"], ["Data exported completely", "Deletion removes all data", "Consent tracked per user", "Settings apply correctly"]),
            ("Fraud Detection", ["Detect suspicious booking patterns", "Payment fraud scoring", "Account takeover prevention", "Automated blocking of high-risk transactions"], ["Suspicious patterns flagged", "Fraud scores calculated", "Takeover attempts blocked", "High-risk transactions held"]),
            ("Social Sharing", ["Share trip plans on social media", "Invite friends to group trips", "Travel feed showing friends trips", "Collaborative trip planning"], ["Trip shared with preview", "Friends receive invitations", "Feed shows friends activity", "Multiple people edit trip"]),
            ("Waitlist and Price Watch", ["Waitlist for sold-out flights", "Price watch for specific routes", "Notification on availability or price change", "Auto-book when conditions met"], ["Waitlist added correctly", "Price tracked over time", "Notifications sent on change", "Auto-book executes correctly"]),
        ]
    },
    {
        "file": "24_ecommerce_marketplace.json",
        "title": "Multi-Vendor eCommerce Marketplace",
        "tech": ["Next.js", "Node.js", "MongoDB", "Elasticsearch", "Stripe"],
        "frs": [
            ("Vendor Registration", ["Apply to become a seller with business details", "Document verification for business license", "Multi-step onboarding wizard", "Admin approval workflow"], ["Application submitted", "Documents verified", "Onboarding completed", "Admin approves/rejects"]),
            ("Vendor Store Setup", ["Customize storefront with logo and banner", "Set shipping policies", "Configure return policies", "Working hours and vacation mode"], ["Storefront customized", "Shipping policies applied", "Return policy displayed", "Vacation mode pauses listings"]),
            ("Product Listing", ["Add products with title, description, images", "Product variants with different prices", "Category and subcategory assignment", "SEO fields for product pages"], ["Product listed successfully", "Variants display correctly", "Category assignment works", "SEO fields indexed"]),
            ("Product Approval", ["Admin reviews new product listings", "Quality check for images and descriptions", "Category verification", "Prohibited items detection"], ["Reviews queued for admin", "Quality issues flagged", "Category verified", "Prohibited items blocked"]),
            ("Multi-vendor Cart", ["Cart supports items from multiple vendors", "Shipping calculated per vendor", "Group items by vendor in cart", "Clear vendor identification"], ["Multiple vendor items in cart", "Per-vendor shipping shown", "Items grouped correctly", "Vendor names displayed"]),
            ("Checkout with Split Payment", ["Single checkout for multi-vendor orders", "Payment split to vendors per commission", "Platform commission deduction", "Transaction fee handling"], ["Checkout processes all items", "Payment split correctly", "Commission deducted", "Fees handled properly"]),
            ("Order Routing", ["Route order items to respective vendors", "Vendor receives their order portion", "Independent fulfillment per vendor", "Consolidated order tracking for buyer"], ["Items routed to correct vendor", "Vendor sees their items only", "Each vendor ships independently", "Buyer sees unified tracking"]),
            ("Vendor Dashboard", ["Sales overview and revenue charts", "Order management with status updates", "Inventory monitoring", "Customer message management"], ["Sales data accurate", "Orders manageable", "Inventory tracked", "Messages accessible"]),
            ("Commission Management", ["Set commission rates per category", "Volume-based commission tiers", "Commission reports for vendors", "Payout scheduling"], ["Rates apply per category", "Tiers calculate correctly", "Reports show commission details", "Payouts processed on schedule"]),
            ("Vendor Payouts", ["Schedule weekly or monthly payouts", "Payout to bank account or PayPal", "Minimum payout threshold", "Payout history and statements"], ["Payouts run on schedule", "Methods process correctly", "Threshold enforced", "History accurate"]),
            ("Product Search", ["Full-text search across all vendors", "Filter by price, rating, vendor, category", "Sort by relevance, price, newest", "Auto-suggest while typing"], ["Search returns relevant results", "Filters work correctly", "Sort updates order", "Suggestions appear quickly"]),
            ("Review System", ["Buyers review products and vendors", "Photo reviews support", "Vendor response to reviews", "Review aggregation and scoring"], ["Reviews submitted", "Photos display with review", "Responses shown under review", "Scores aggregate correctly"]),
            ("Dispute Resolution", ["Buyer opens dispute for order issues", "Evidence submission by both parties", "Admin mediation workflow", "Refund or resolution enforcement"], ["Dispute created with details", "Evidence uploaded by both", "Admin reviews and decides", "Resolution enforced"]),
            ("Shipping Integration", ["Multiple shipping carrier integrations", "Real-time shipping rate calculation", "Tracking number assignment", "Delivery confirmation"], ["Carriers available in checkout", "Rates calculated correctly", "Tracking assigned and trackable", "Delivery status updated"]),
            ("Return and Refund", ["Buyer initiates return request", "Vendor approves or declines return", "Return shipping label generation", "Refund processing on return receipt"], ["Return request submitted", "Vendor reviews request", "Label generated", "Refund processed"]),
            ("Coupons and Promotions", ["Platform-wide coupon codes", "Vendor-specific discount offers", "Flash sales with countdown timers", "Buy-one-get-one promotions"], ["Platform coupons apply", "Vendor discounts work", "Timer counts down accurately", "BOGO adds free item"]),
            ("Wishlist", ["Save products to wishlist", "Price drop notifications for saved items", "Move to cart from wishlist", "Share wishlist with others"], ["Products saved", "Price alerts sent", "Move to cart works", "Shared link accessible"]),
            ("Messaging System", ["Buyer-vendor communication", "Pre-purchase questions", "Order-related messages", "Automated responses for common questions"], ["Messages delivered", "Questions linked to products", "Messages linked to orders", "Auto-responses trigger"]),
            ("Category Management", ["Hierarchical category tree", "Category attributes and specifications", "Featured categories on homepage", "Category-specific filters"], ["Tree structure works", "Attributes display on products", "Featured shown on home", "Filters relevant to category"]),
            ("SEO and Marketing", ["Product page SEO optimization", "Sitemap generation", "Social media meta tags", "Email marketing campaigns"], ["SEO meta tags populated", "Sitemap generated", "Social previews correct", "Campaigns sent to segments"]),
            ("Analytics for Platform", ["GMV and revenue tracking", "Vendor performance metrics", "Buyer behavior analytics", "Conversion funnel reports"], ["GMV matches transactions", "Vendor metrics accurate", "Behavior tracked correctly", "Funnel shows conversions"]),
            ("Tax Management", ["Tax calculation per jurisdiction", "Tax-exempt customer handling", "Tax reports for vendors", "Automated tax filing integration"], ["Tax calculated correctly", "Exemptions applied", "Reports show tax collected", "Filing data exported"]),
            ("Inventory Sync", ["Vendor syncs inventory from external system", "Stock level auto-update", "Out-of-stock auto-hide", "Low stock alerts to vendor"], ["Sync imports correctly", "Levels update in real-time", "OOS products hidden", "Alerts sent at threshold"]),
            ("Mobile App", ["Native mobile shopping experience", "Push notifications for offers and orders", "Barcode scanner for product lookup", "Mobile-optimized checkout"], ["App functions fully", "Notifications received", "Scanner identifies products", "Checkout completes on mobile"]),
            ("Content Management", ["Homepage banner management", "Landing page builder", "Blog and article publishing", "FAQ management"], ["Banners display correctly", "Landing pages render", "Articles published and indexed", "FAQs searchable"]),
            ("User Account", ["Registration and login", "Order history and tracking", "Address book management", "Account settings and preferences"], ["Account created", "History shows all orders", "Addresses manageable", "Settings saved"]),
            ("Recommendation Engine", ["Personalized product recommendations", "Recently viewed products", "Frequently bought together", "Category-based trending"], ["Recommendations relevant", "Recent items shown", "Cross-sells displayed", "Trending items current"]),
            ("Subscription Products", ["Recurring purchase subscriptions", "Subscription management by buyer", "Auto-billing on schedule", "Skip or pause subscription"], ["Subscription created", "Management options available", "Billing runs on schedule", "Skip/pause works"]),
            ("Bulk Operations", ["Vendor bulk product upload via CSV", "Bulk price updates", "Bulk inventory adjustment", "Bulk order status update"], ["CSV import processes", "Prices update in bulk", "Inventory adjusted", "Orders status changed"]),
            ("Compliance and Legal", ["Terms of service management", "Privacy policy display", "GDPR data export and deletion", "Copyright infringement reporting"], ["ToS displayed and accepted", "Privacy policy accessible", "Data exported/deleted", "DMCA reports processed"]),
            ("Multi-currency", ["Display prices in buyer's currency", "Currency conversion at checkout", "Vendor receives in their currency", "Exchange rate management"], ["Prices display in local currency", "Conversion accurate", "Vendor paid in their currency", "Rates updated daily"]),
            ("Warehouse Fulfillment", ["Platform fulfillment option for vendors", "Warehouse inventory receiving", "Pick, pack, ship workflow", "Returns processing at warehouse"], ["Fulfillment option available", "Receiving updates inventory", "Workflow stages tracked", "Returns processed"]),
            ("Fraud Prevention", ["Suspicious order detection", "Address verification", "Chargeback management", "Buyer account risk scoring"], ["Suspicious orders flagged", "Address verified", "Chargebacks tracked", "Risk scores calculated"]),
        ]
    },
]

# ── More domain definitions ───────────────────────────────────────
MORE_DOMAINS = [
    ("25_insurance.json", "Insurance Management Platform", ["React", "Java Spring Boot", "Oracle DB", "RabbitMQ"], [
        "Policy Browsing and Comparison", "Quote Generation", "Online Policy Purchase", "KYC Document Upload", "Premium Payment", "Policy Renewal", "Claims Submission", "Claims Document Upload", "Claims Assessment Workflow", "Claims Payment Processing",
        "Policy Amendment", "Beneficiary Management", "Rider and Add-on Management", "Policy Cancellation and Surrender", "Agent Portal", "Agent Commission Tracking", "Underwriting Workflow", "Risk Assessment Engine", "Customer Portal Dashboard", "Communication Preferences",
        "Document Generation", "Email and SMS Notifications", "Payment Gateway Integration", "Auto-debit Setup for Premiums", "Grace Period Management", "Lapse and Revival Process", "Reinsurance Management", "Actuarial Reports", "Compliance Reporting", "Audit Trail",
        "Customer Grievance System", "Third-party Administrator Integration", "Health Network Hospital Search", "Cashless Claim Authorization", "Maturity and Survival Benefit Processing", "Nomination and Assignment", "Loan Against Policy", "Fund Transfer Between Plans",
        "NAV Calculation for ULIP", "Premium Calculator Widget", "Mobile App Access", "Chat Support Integration", "Admin Analytics Dashboard", "Performance Reporting for Agents", "Bulk Policy Import"
    ]),
    ("26_fleet_management.json", "Fleet Management System", ["React", "Node.js", "PostgreSQL", "InfluxDB"], [
        "Vehicle Registration", "Driver Registration and Licensing", "Vehicle Assignment to Driver", "GPS Real-time Tracking", "Route Planning and Optimization", "Trip Management", "Fuel Consumption Tracking", "Fuel Card Integration", "Maintenance Scheduling",
        "Preventive Maintenance Alerts", "Breakdown and Repair Logging", "Tire Management", "Vehicle Inspection Checklists", "Driver Behavior Monitoring", "Speed and Harsh Braking Alerts", "Geofencing Setup and Alerts", "Idle Time Tracking", "Mileage Tracking",
        "Driver Scorecard", "Trip History and Reports", "Fuel Efficiency Reports", "Maintenance Cost Reports", "Vehicle Utilization Analytics", "Fleet Dashboard Overview", "Driver License Expiry Alerts", "Insurance Renewal Tracking", "Registration Renewal Alerts",
        "Document Storage per Vehicle", "Accident and Incident Recording", "Driver Training Management", "Compliance Reporting", "Carbon Emission Tracking", "Vehicle Disposal and Lifecycle", "Spare Parts Inventory", "Vendor Management for Repairs",
        "Driver Attendance and Shift Scheduling", "Mobile App for Drivers", "Push Notifications", "API Integration for Telematics", "Admin Role Management", "Multi-depot Support", "Cost Per Kilometer Analysis"
    ]),
    ("27_pos_retail.json", "Point of Sale and Retail Management", ["React", "Node.js", "PostgreSQL", "Redis"], [
        "Product Management with Barcode", "Category and Subcategory Management", "Inventory Tracking", "Multi-store Inventory Sync", "Purchase Order Management", "Supplier Management", "Stock Transfer Between Stores", "Sales Transaction Processing",
        "Barcode Scanning at Checkout", "Cash Register Management", "Multiple Payment Methods", "Receipt Generation and Printing", "Customer Registration", "Customer Loyalty Program", "Discount and Coupon Application", "Tax Calculation by Region",
        "Daily Sales Reports", "Product Return and Exchange", "Gift Card System", "Employee Management", "Employee Shift Scheduling", "Role-based Access Control", "Sales Commission Tracking", "Price Label Printing", "Stock Count and Reconciliation",
        "Low Stock Alerts and Auto-reorder", "Expiry Date Tracking", "Layaway Management", "Sales Analytics Dashboard", "Customer Purchase History", "Profit and Loss Reports", "Multi-currency Support", "Offline Mode for POS", "Cloud Sync When Online",
        "Kitchen Display for Restaurant POS", "Table Management for Restaurants", "Delivery Order Management", "Promotions and Happy Hour", "End of Day Reporting", "Cash Drawer Management"
    ]),
    ("28_dating_app.json", "Dating and Social Matching Application", ["React Native", "Node.js", "MongoDB", "Redis", "Firebase"], [
        "User Registration with Phone Verification", "Profile Creation with Photos and Bio", "Identity Verification with Selfie", "Preference Settings", "Swipe-based Matching", "Advanced Search with Filters", "Match Queue and Discovery",
        "Match Notification System", "Chat Messaging for Matches", "Voice and Video Calling", "Read Receipts and Typing Indicators", "Photo and Media Sharing in Chat", "Ice Breaker Questions", "Super Like Feature", "Boost Profile Visibility",
        "Premium Subscription Plans", "Undo Last Swipe", "See Who Liked You", "Location-based Discovery", "Travel Mode for Different Cities", "Profile Verification Badge", "Block and Report Users", "Content Moderation for Photos",
        "Safety Features and Emergency Contacts", "Date Check-in Feature", "Profile Prompts and Questions", "Interests and Hobbies Tags", "Compatibility Score Calculation", "Event and Activity Discovery", "Group Dating Feature",
        "Profile Analytics for Premium Users", "Push Notification Preferences", "Ghost Mode and Incognito", "Profile Deactivation and Deletion", "Admin Moderation Dashboard", "User Ban and Appeal Process", "Analytics and Growth Metrics",
        "A/B Testing Framework", "Referral Program", "In-app Purchase Management"
    ]),
    ("29_legaltech.json", "Legal Practice Management System", ["React", "Python Django", "PostgreSQL"], [
        "Client Intake and Registration", "Matter and Case Creation", "Case Timeline and Activity Log", "Document Management and Versioning", "Document Template Engine", "Contract Drafting and Review", "E-signature Integration", "Court Calendar Management",
        "Deadline and Statute Tracking", "Task Assignment and Tracking", "Time Tracking and Billable Hours", "Invoice Generation", "Trust Account Management", "Payment Processing", "Conflict of Interest Checking", "Client Communication Portal",
        "Secure Messaging", "Email Integration", "Legal Research Notes", "Precedent Database", "Court Filing Integration", "Expense Tracking per Case", "Team Calendar and Scheduling", "Role-based Access Control", "Audit Trail for All Actions",
        "Client Reporting Dashboard", "Matter Budget Tracking", "Billing Rate Management", "Retainer Management", "Accounts Receivable Aging", "Custom Report Builder", "Practice Area Analytics", "Leads and Business Development",
        "Knowledge Base Management", "Workflow Automation Rules", "Form Builder for Intake"
    ]),
    ("30_smart_home.json", "Smart Home IoT Platform", ["React", "Node.js", "MongoDB", "MQTT", "InfluxDB"], [
        "Device Registration and Pairing", "Room and Zone Management", "Device Control Dashboard", "Light Control with Dimming", "Thermostat Management", "Security Camera Live Feed", "Motion Sensor Alerts", "Door Lock Remote Control",
        "Garage Door Control", "Smoke and CO Detector Alerts", "Water Leak Detection", "Energy Consumption Monitoring", "Scene Creation and Automation", "Schedule-based Automation", "Trigger-based Rules Engine", "Voice Assistant Integration",
        "Geofencing for Home/Away", "Multi-user Access Control", "Guest Access Management", "Activity and Event Logging", "Push Notification Alerts", "Historical Data Charts", "Device Firmware Updates", "Device Health Monitoring",
        "Battery Level Tracking", "Intercom and Doorbell", "Window Shade Control", "Sprinkler System Control", "Pet Feeder Integration", "Music System Control", "Home Security Arming", "Panic Button and Emergency Alert",
        "Energy Billing Integration", "Solar Panel Monitoring", "EV Charger Management", "Maintenance Reminders", "Mobile App Control", "Widget for Quick Actions", "Third-party Device API", "Admin Dashboard and Analytics"
    ]),
    ("31_restaurant_mgmt.json", "Restaurant Management System", ["React", "Node.js", "PostgreSQL"], [
        "Menu Management with Categories", "Menu Item Variants and Modifiers", "Seasonal and Special Menus", "Digital Menu QR Code Generation", "Table Reservation System", "Walk-in Queue Management", "Table Layout and Floor Plan", "Order Taking by Waitstaff",
        "Customer Self-ordering via QR", "Kitchen Display System", "Order Priority and Timing", "Course Management for Fine Dining", "Split Bill and Merged Tabs", "Payment Processing", "Tip Management", "Receipt and Invoice Generation",
        "Inventory and Stock Tracking", "Recipe and Ingredient Management", "Supplier and Purchase Orders", "Waste Tracking", "Staff Scheduling and Shifts", "Staff Time Clock", "Payroll Integration", "Delivery Order Management",
        "Third-party Delivery Integration", "Online Ordering Website", "Customer Loyalty Program", "Gift Card System", "Customer Feedback and Reviews", "Allergen and Dietary Information", "Nutritional Information Display", "Happy Hour and Promotions",
        "Daily and Weekly Sales Reports", "Food Cost Analysis", "Revenue and Profit Reports", "Customer Analytics", "Multi-location Management", "Franchise Management", "Health Inspection Compliance", "CCTV Integration", "Admin Dashboard"
    ]),
    ("32_logistics.json", "Logistics and Shipping Platform", ["React", "Go", "PostgreSQL", "Redis", "RabbitMQ"], [
        "Shipment Booking", "Rate Calculation by Weight and Distance", "Multi-carrier Rate Comparison", "Pickup Scheduling", "Label and Document Generation", "Barcode and QR Code Tracking", "Real-time Shipment Tracking", "Delivery Status Updates",
        "Proof of Delivery with Photo", "Electronic Signature Capture", "Failed Delivery Reattempt Scheduling", "Return Shipment Management", "Cash on Delivery Collection", "Warehouse Receiving", "Warehouse Storage Management", "Order Picking and Packing",
        "Dispatch and Route Optimization", "Driver Assignment", "Driver Mobile App", "Vehicle Tracking GPS", "Geofencing for Delivery Zones", "Delivery Time Window Management", "Customer Notification via SMS and Email", "Customer Portal for Tracking",
        "Billing and Invoicing", "Automated Invoice Generation", "Payment Collection and Reconciliation", "Vendor and Partner Management", "SLA Monitoring and Alerts", "Exception Management", "Damage and Loss Claims", "Insurance Integration",
        "Customs and Cross-border Documentation", "Temperature-controlled Shipping", "Fragile Item Handling Protocols", "Bulk Shipment Processing", "API for eCommerce Integration", "Webhook Notifications", "Analytics and KPI Dashboard", "Route Performance Reports",
        "Cost per Shipment Analysis", "Carbon Footprint Tracking", "Admin User Management", "Multi-branch Support"
    ]),
    ("33_crowdfunding.json", "Crowdfunding Platform", ["Next.js", "Node.js", "PostgreSQL", "Stripe"], [
        "Creator Registration", "Campaign Creation with Goal and Timeline", "Rich Media Campaign Page", "Reward Tier Management", "Campaign Preview and Draft", "Campaign Approval by Admin", "Campaign Discovery and Search", "Category Browsing",
        "Trending and Featured Campaigns", "Backer Registration", "Pledge and Reward Selection", "Payment Processing for Pledges", "Stretch Goals", "Campaign Updates and Posts", "Backer Comments and Discussion", "Creator Messaging to Backers",
        "Campaign Progress Tracking", "Social Sharing Integration", "Email Campaign to Backers", "Referral and Ambassador Program", "Early Bird Rewards", "Limited Quantity Rewards", "Add-on Purchases", "Shipping Address Collection from Backers",
        "International Shipping Options", "Reward Fulfillment Tracking", "Backer Survey for Customization", "Tax and VAT Handling", "Platform Fee Management", "Creator Payout Processing", "Refund Policy and Processing", "Campaign Extension Requests",
        "Failed Campaign Handling", "Analytics for Creators", "Platform Analytics Dashboard", "Content Moderation", "Fraud Detection for Campaigns", "Identity Verification for Creators", "Community Guidelines Enforcement", "API for Third-party Integration"
    ]),
    ("34_property_mgmt.json", "Property and Tenant Management", ["React", "Django", "PostgreSQL"], [
        "Property Registration with Details", "Unit and Apartment Management", "Photo Gallery per Property", "Tenant Application Processing", "Background Check Integration", "Lease Agreement Generation", "E-signature for Lease", "Rent Collection Online",
        "Automated Rent Reminders", "Late Fee Calculation", "Security Deposit Management", "Maintenance Request Submission", "Maintenance Work Order Assignment", "Vendor Management for Repairs", "Maintenance Tracking and History", "Common Area Booking",
        "Amenity Management", "Visitor Management", "Package Delivery Tracking", "Parking Space Assignment", "Pet Registration", "Tenant Communication Portal", "Emergency Broadcast System", "Document Sharing with Tenants",
        "Utility Billing and Tracking", "Property Inspection Scheduling", "Inspection Checklist and Photos", "Insurance Tracking per Property", "Tax Document Management", "Financial Reporting per Property", "Vacancy Listing and Marketing",
        "Rental Listing on External Sites", "Applicant Comparison Tool", "Lease Renewal Management", "Move-in and Move-out Checklists", "Key and Access Management", "HOA Fee Management", "Owner Portal and Reports", "Multi-property Dashboard",
        "Admin Role-based Access"
    ]),
    ("35_fitness_social.json", "Fitness Social Network", ["React Native", "Node.js", "MongoDB", "Redis"], [
        "User Registration with Fitness Goals", "Profile with Stats and Achievements", "Workout Logging with Exercises", "Custom Workout Creation", "Workout Plan Templates", "Exercise Video Library", "Personal Record Tracking", "Progress Photo Timeline",
        "Body Measurement Tracking", "Nutrition and Macro Tracking", "Meal Logging with Food Database", "Water Intake Tracking", "Calorie and Macro Budget", "Social Feed with Workout Posts", "Like and Comment on Workouts", "Follow Other Users",
        "Workout Challenges and Competitions", "Leaderboards", "Achievement Badges and Milestones", "Streak Tracking", "Wearable Device Integration", "Heart Rate Zone Tracking", "Sleep Tracking Integration", "Step Counter Dashboard",
        "Group Workout Sessions", "Virtual Live Classes", "Personal Trainer Marketplace", "Trainer Client Management", "Training Program Sales", "In-app Purchase for Programs", "Progress Reports and Analytics", "Goal Setting and Tracking",
        "Workout Reminders and Scheduling", "Rest Day Recommendations", "Community Forums", "Direct Messaging", "Push Notifications", "Admin Content Moderation", "Analytics Dashboard", "Subscription Management"
    ]),
    ("36_auction.json", "Online Auction Platform", ["React", "Node.js", "PostgreSQL", "Redis", "WebSocket"], [
        "Seller Registration and Verification", "Item Listing with Photos and Description", "Starting Price and Reserve Price", "Auction Duration and Scheduling", "Category and Tag Management", "Item Condition Grading", "Buyer Registration",
        "Real-time Bidding with WebSocket", "Auto-bid Maximum Setting", "Bid Increment Rules", "Bid History Display", "Outbid Notification", "Auction Countdown Timer", "Auction Extension on Late Bids", "Buy It Now Option",
        "Watchlist for Auctions", "Search and Filter Auctions", "Featured and Promoted Listings", "Auction Results and Winner", "Post-auction Payment Processing", "Escrow Payment Holding", "Shipping Label Generation", "Delivery Tracking",
        "Seller Rating and Feedback", "Buyer Rating and Feedback", "Dispute Resolution Process", "Item Authentication Service", "Live Auction Streaming", "Mobile Bidding App", "Push Notifications for Bids", "Seller Dashboard and Analytics",
        "Sales History and Reports", "Platform Commission Management", "Payout to Sellers", "Proxy Bidding System", "Charity Auction Support", "Multi-currency Bidding", "Admin Auction Management", "Content Moderation", "Fraud Detection System"
    ]),
    ("37_expense_mgmt.json", "Corporate Expense Management", ["React", "Node.js", "PostgreSQL"], [
        "Employee Registration and Onboarding", "Expense Policy Configuration", "Expense Report Creation", "Receipt Photo Capture", "OCR Receipt Scanning", "Expense Categories and Tags", "Per Diem Configuration", "Mileage Tracking and Calculation",
        "Multi-currency Expense Entry", "Exchange Rate Management", "Manager Approval Workflow", "Multi-level Approval Chains", "Policy Violation Flagging", "Budget Tracking per Department", "Project-based Expense Tracking", "Credit Card Transaction Import",
        "Bank Feed Integration", "Duplicate Detection", "Tax Reclaim Tracking", "Reimbursement Processing", "Direct Deposit for Reimbursement", "Advance Request and Settlement", "Vendor Payment Management", "Corporate Card Management",
        "Spending Limit Configuration", "Real-time Budget vs Actual", "Department Expense Reports", "Employee Expense History", "Monthly Expense Summary", "Annual Tax Report Generation", "Audit Trail for Approvals", "ERP Integration",
        "Accounting Software Sync", "Custom Report Builder", "Analytics Dashboard", "Mobile App for Submissions", "Offline Receipt Capture", "Push Notification for Approvals", "Admin Configuration Panel", "Role-based Access Control"
    ]),
    ("38_volunteer.json", "Volunteer Management Platform", ["React", "Python Flask", "PostgreSQL"], [
        "Volunteer Registration", "Skills and Interest Profiling", "Availability Calendar Setup", "Background Check Integration", "Organization Registration", "Event and Opportunity Posting", "Volunteer Search and Matching", "Application to Opportunities",
        "Volunteer Assignment and Scheduling", "Shift Management", "Hour Logging and Verification", "Supervisor Approval of Hours", "Certificate Generation", "Impact Reporting per Volunteer", "Team and Group Management", "Communication and Messaging",
        "Event Check-in with QR Code", "Waiver and Consent Management", "Training Module Assignment", "Training Completion Tracking", "Donation Integration", "Fundraiser Event Management", "Social Media Sharing", "Volunteer Leaderboard",
        "Recognition and Awards", "Feedback and Survey System", "Recurring Commitment Management", "Emergency Contact Management", "GDPR-compliant Data Handling", "Report Generation", "Analytics Dashboard", "Mobile App Access",
        "Push Notifications", "Email Campaign Management", "API for Partner Integration", "Multi-organization Support"
    ]),
    ("39_music_streaming.json", "Music Streaming Service", ["React", "Go", "PostgreSQL", "Redis", "S3"], [
        "User Registration and Profile", "Subscription Plan Management", "Free Tier with Ads", "Music Library Browsing", "Album and Artist Pages", "Song Search with Autocomplete", "Playlist Creation and Management", "Collaborative Playlists",
        "Music Playback with Controls", "Queue Management", "Shuffle and Repeat Modes", "Crossfade Between Tracks", "Lyrics Display", "Music Discovery and Recommendations", "Personalized Daily Mixes", "Genre and Mood-based Stations",
        "Radio Mode from Song or Artist", "Social Features and Following", "Share Songs and Playlists", "Friend Activity Feed", "Download for Offline Listening", "Audio Quality Settings", "Equalizer Settings", "Chromecast and AirPlay Support",
        "Car Mode Interface", "Sleep Timer", "Listening History and Stats", "Annual Listening Wrapped Report", "Artist Profile Management", "Artist Analytics Dashboard", "Music Upload for Artists", "Album Release Scheduling",
        "Royalty Calculation and Reporting", "Ad Insertion for Free Tier", "Podcast Integration", "Podcast Episode Management", "Like and Save Songs", "Blocked Artists and Songs", "Parental Controls", "Admin Content Management",
        "Copyright Claim Management", "Platform Analytics"
    ]),
    ("40_subscription_box.json", "Subscription Box Service", ["Next.js", "Node.js", "PostgreSQL", "Stripe"], [
        "Customer Registration", "Quiz-based Preference Collection", "Subscription Plan Selection", "Custom Box Configuration", "Recurring Billing Setup", "Skip Month Option", "Pause Subscription", "Cancel Subscription with Survey",
        "Payment Method Management", "Address Management", "Gift Subscription Purchase", "Gift Message and Delivery Date", "Box Curation by Admin", "Product Selection for Box", "Supplier Product Management", "Inventory for Box Items",
        "Box Assembly Workflow", "Shipping Label Generation", "Tracking Integration", "Delivery Notification", "Unboxing Experience Rating", "Product Review per Item", "Preference Update from Ratings", "Referral Program",
        "Loyalty Points System", "Add-on Purchase with Subscription", "Past Box Gallery", "Upcoming Box Preview", "Waitlist for Sold-out Plans", "Limited Edition Box Management", "Collaboration Box with Brands", "Customer Support Chat",
        "FAQ and Help Center", "Return and Exchange", "Admin Dashboard", "Revenue and Churn Analytics", "Subscriber Demographics", "A/B Testing for Box Contents", "Email Marketing Campaigns", "Social Media Integration"
    ]),
]

def generate_fr_data(title, requirements_text, acceptance_text=None):
    """Generate FR entry aligned with the latest SRS format."""
    reqs = requirements_text if isinstance(requirements_text, list) else [requirements_text]
    entry = {
        "title": title,
        "requirements": reqs,
    }
    if acceptance_text:
        acs = acceptance_text if isinstance(acceptance_text, list) else [acceptance_text]
        entry["acceptance_criteria"] = acs
    return entry


def build_project_input(title, techs, frs):
    """Build richer training input aligned with the production SRS schema."""
    module_titles = [fr["title"] for fr in frs.values()][:10]
    actor_defaults = ["Admin", "Manager", "Employee", "User"]
    scope = [f"{fr['title']} workflows" for fr in list(frs.values())[:6]]

    backend_stack = [tech for tech in techs if tech.lower() not in {"react", "next.js", "angular", "vue", "vue.js", "react native"}]
    operating_environment = {
        "frontend": f"Web-based interface built with {techs[0]} and accessible through modern browsers.",
        "backend": f"Service layer implemented with {', '.join(backend_stack) if backend_stack else 'REST APIs'} for business operations.",
        "deployment": "Cloud-hosted environment with centralized monitoring, backups, and automated deployments.",
    }

    non_functional_requirements = {
        "NFR-01": {
            "title": "Security and Access Control",
            "requirements": [
                "All sensitive data must be encrypted in transit and at rest",
                "Role-based authorization must restrict access by module and action",
                "All authentication events and privileged actions must be logged",
            ],
        },
        "NFR-02": {
            "title": "Performance and Scalability",
            "requirements": [
                "Core pages and dashboards should load within acceptable enterprise SLAs",
                "The platform must support concurrent usage across multiple departments",
                "Background jobs and reporting workloads should not block transactional workflows",
            ],
        },
        "NFR-03": {
            "title": "Reliability and Recoverability",
            "requirements": [
                "Automated backups must run on a defined schedule",
                "Critical workflows should support retry-safe processing and audit logging",
                "Operational alerts should be generated for failures and degraded services",
            ],
        },
    }

    return {
        "title": title,
        "description": f"{title} is a web-based enterprise platform that centralizes operational workflows, data visibility, and cross-functional reporting.",
        "technologies": techs,
        "actors": actor_defaults,
        "user_classes": {
            "Admin": "Configures the system, manages users, and oversees permissions and settings.",
            "Manager": "Oversees departmental workflows, approvals, KPIs, and operational reporting.",
            "Employee": "Performs day-to-day operational tasks within assigned modules and permissions.",
            "User": "Generic authenticated platform user with access limited by role and department.",
        },
        "definitions": {
            "Admin": "System user with full administrative privileges.",
            "Manager": "Operational owner of a department, module, or workflow.",
            "Employee": "End user performing role-specific business operations.",
        },
        "modules": module_titles,
        "scope": scope,
        "constraints": [
            "Initial release will focus on the web platform only",
            "Role-based access control is mandatory across all modules",
            "Operational data must be auditable and retained according to policy",
        ],
        "operating_environment": operating_environment,
        "non_functional_requirements": non_functional_requirements,
        "system_attributes": {
            "reliability": "Platform should provide resilient transactional processing with backup and recovery capabilities.",
            "scalability": "Architecture should support horizontal scaling for APIs, background workers, and reporting services.",
            "security": "Authentication, authorization, encryption, and auditability must be built into every module.",
            "maintainability": "Codebase should remain modular, observable, and safe to extend through clear service boundaries.",
        },
        "out_of_scope": [
            "Native mobile applications in the first release",
            "Large third-party marketplace or legacy ERP migrations unless explicitly scoped",
            "Non-core experimental modules outside the platform's operational workflows",
        ],
        "functional_requirements": frs,
    }


def build_task_acceptance_criteria(task_type, fr_title, domain_title):
    """Create task-level definition of done for training outputs."""
    feature_lower = fr_title.lower()

    if task_type == "design":
        return [
            f"UI design for {feature_lower} is complete and reviewable.",
            f"The {feature_lower} design is responsive and accessible.",
            f"The design for {feature_lower} aligns with the documented user flow and validation states.",
        ]

    if task_type == "frontend":
        return [
            f"Frontend implements the required {feature_lower} user interactions.",
            f"Validation, loading, and error states for {feature_lower} are handled in the UI.",
            f"Frontend behavior for {feature_lower} is integrated correctly with backend APIs.",
        ]

    if task_type == "backend":
        return [
            f"Backend logic for {feature_lower} is implemented and testable.",
            f"APIs and business rules for {feature_lower} enforce validation and security requirements.",
            f"Data handling for {feature_lower} is reliable and supports the required workflow.",
        ]

    if task_type == "testing":
        return [
            f"Tests cover the main success and failure scenarios for {feature_lower}.",
            f"Security, validation, and permission checks for {feature_lower} are verified.",
            f"Regression coverage exists for the most important {feature_lower} behaviors.",
        ]

    if task_type == "database":
        return [
            f"The data model for {feature_lower} supports the required workflow.",
            f"Relationships, constraints, and indexes for {feature_lower} are defined correctly.",
            f"Schema changes for {feature_lower} can be applied safely in target environments.",
        ]

    if task_type == "security":
        return [
            f"Security controls for {feature_lower} enforce the required authentication, authorization, or data-protection rules.",
            f"Sensitive operations and failure scenarios for {feature_lower} are logged, validated, and protected against misuse.",
            f"The implementation of {feature_lower} satisfies the relevant privacy, audit, or compliance expectations in the SRS.",
        ]

    if task_type == "integration":
        return [
            f"External or cross-system integrations required by {feature_lower} exchange the expected payloads successfully.",
            f"Retry, timeout, and failure handling for {feature_lower} integrations are implemented and observable.",
            f"Credentials, tokens, and outbound calls used by {feature_lower} are configured and secured correctly.",
        ]

    if task_type == "devops":
        return [
            f"Operational setup for {feature_lower} covers deployment, configuration, and environment readiness.",
            f"Monitoring, alerting, backup, or recovery controls relevant to {feature_lower} are in place and verifiable.",
            f"The runtime behavior of {feature_lower} can be observed, supported, and recovered in target environments.",
        ]

    return [
        f"The {feature_lower} task is implemented and verifiable.",
        f"Edge cases for {feature_lower} are handled cleanly.",
        f"Relevant stakeholders can validate the completed {feature_lower} workflow.",
    ]


def summarize_requirements(requirements, limit=3):
    """Extract the most important requirement bullets for task descriptions."""
    cleaned = [str(item).strip().rstrip(".") for item in (requirements or []) if str(item).strip()]
    return cleaned[:limit]


def has_any_signal(signals, keywords):
    """Check whether any keyword or phrase appears in the normalized signal text."""
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", signals)
        for keyword in keywords
    )


def create_task(fr_id, fr_title, domain_title, task_title, description, priority, task_type, acceptance_criteria):
    """Create a normalized detailed task."""
    return {
        "title": task_title,
        "description": description,
        "priority": priority,
        "type": task_type,
        "related_requirement": fr_id,
        "acceptance_criteria": acceptance_criteria,
    }


def generate_tasks_for_fr(fr_id, fr_title, domain_title, techs, fr_data=None):
    """Generate realistic role-based tasks for a functional requirement."""
    feature_lower = fr_title.lower()
    requirements = summarize_requirements((fr_data or {}).get("requirements", []), limit=4)
    requirement_summary = "; ".join(requirements[:3]) if requirements else f"core {feature_lower} workflow requirements"
    signals = " ".join([feature_lower, requirement_summary]).lower()

    integration_keywords = [
        "sso", "google", "facebook", "microsoft", "payment", "gateway",
        "email", "sms", "api", "import", "export", "bank",
        "third-party", "third party", "webhook", "insurance",
        "exchange rate", "single sign-on",
    ]
    security_keywords = [
        "authentication", "authorization", "role-based", "rbac", "permission",
        "security", "privacy", "encryption", "audit", "audit trail",
        "audit log", "logging", "logs", "compliance", "fraud",
        "verification", "controlled substance", "access control",
    ]
    database_keywords = [
        "record", "records", "profile", "inventory", "order", "payment",
        "transaction", "document", "supplier", "vendor", "ticket", "asset",
        "employee", "patient", "history", "tracking", "queue", "catalog",
        "report", "dashboard", "booking", "reservation", "reconciliation",
        "upload", "storage", "batch", "attendance", "payroll", "campaign",
    ]
    devops_keywords = [
        "backup", "restore", "availability", "downtime",
        "observability", "scaling", "scalability", "deployment",
        "infrastructure", "recovery", "uptime", "disaster",
        "firmware update", "health monitoring", "system availability",
        "failover", "maintenance window",
    ]
    backend_only_keywords = [
        "encryption", "backup", "restore", "availability", "downtime",
        "deployment", "infrastructure", "observability", "fraud", "reconciliation",
    ]
    ux_override_keywords = [
        "dashboard", "portal", "management", "settings", "configuration",
        "report", "analytics", "monitoring", "alert", "notification", "tracking",
    ]

    needs_integration = has_any_signal(signals, integration_keywords)
    needs_security = has_any_signal(signals, security_keywords)
    needs_database = has_any_signal(signals, database_keywords)
    needs_devops = has_any_signal(signals, devops_keywords)
    needs_design_frontend = (
        not has_any_signal(signals, backend_only_keywords)
        or has_any_signal(signals, ux_override_keywords)
    )

    tasks = []

    if needs_design_frontend:
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"Design {fr_title} UI",
                f"Design the user interface for {feature_lower}. Create the screens, forms, dashboards, or status views needed by the SRS and make the workflow clear, responsive, and accessible for the target users.",
                "high",
                "design",
                build_task_acceptance_criteria("design", fr_title, domain_title),
            )
        )
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"Frontend Implementation of {fr_title}",
                f"Implement the frontend behavior for {feature_lower}. Build the required user interactions, validation states, loading states, and error handling so the interface supports these behaviors: {requirement_summary}.",
                "high",
                "frontend",
                build_task_acceptance_criteria("frontend", fr_title, domain_title),
            )
        )

    tasks.append(
        create_task(
            fr_id,
            fr_title,
            domain_title,
            f"Backend Implementation of {fr_title}",
            f"Implement the backend logic for {feature_lower}. Build the required APIs, business rules, validation, permissions, persistence, and processing needed to support these behaviors: {requirement_summary}.",
            "high",
            "backend",
            build_task_acceptance_criteria("backend", fr_title, domain_title),
        )
    )

    if needs_database:
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"Database Design for {fr_title}",
                f"Design the data model and persistence strategy for {feature_lower}. Define entities, relationships, indexes, retention rules, and migration changes needed to store and query the workflow reliably.",
                "high",
                "database",
                build_task_acceptance_criteria("database", fr_title, domain_title),
            )
        )

    if needs_security:
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"Security Hardening for {fr_title}",
                f"Implement the security controls required for {feature_lower}. Cover authentication, authorization, encryption, auditing, abuse prevention, and compliance checks where the SRS or workflow calls for them.",
                "high",
                "security",
                build_task_acceptance_criteria("security", fr_title, domain_title),
            )
        )

    if needs_integration:
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"Integrate {fr_title} with External Services",
                f"Integrate {feature_lower} with the external services or providers referenced by the SRS. Implement secure service connections, payload validation, error handling, and recovery behavior for any third-party dependency involved in the workflow.",
                "medium",
                "integration",
                build_task_acceptance_criteria("integration", fr_title, domain_title),
            )
        )

    if needs_devops:
        tasks.append(
            create_task(
                fr_id,
                fr_title,
                domain_title,
                f"DevOps Setup for {fr_title}",
                f"Set up the operational support for {feature_lower}. Configure deployment settings, secrets, background jobs, monitoring, alerting, backup, restore, or recovery controls needed for the feature to run safely in target environments.",
                "medium",
                "devops",
                build_task_acceptance_criteria("devops", fr_title, domain_title),
            )
        )

    tasks.append(
        create_task(
            fr_id,
            fr_title,
            domain_title,
            f"Testing {fr_title} Functionality",
            f"Create and execute tests for {feature_lower}. Cover the main success flows, failure scenarios, permission checks, validation rules, integrations, and operational edge cases described in the SRS so the implementation is safe to release.",
            "high",
            "testing",
            build_task_acceptance_criteria("testing", fr_title, domain_title),
        )
    )

    return tasks

def _feature_slug(title):
    """Normalize a feature title for sentence construction."""
    cleaned = re.sub(r"\s+", " ", title.strip())
    return cleaned.lower() if cleaned else "the feature"


def _build_auth_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"Users must be able to complete {feature} through the approved entry points provided by the platform.",
        f"The system must validate submitted credentials, identity data, and required fields before allowing {feature} to continue.",
        f"{feature_title} must enforce secure handling of sensitive data, failed attempts, and audit logging for security review.",
        f"The user interface for {feature} should provide clear success, failure, and recovery messages for common scenarios.",
    ]


def _build_reporting_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The system must provide {feature} with role-appropriate filters, date ranges, and drill-down views.",
        f"{feature_title} should calculate metrics from current transactional data and keep summaries aligned with source records.",
        f"Authorized users must be able to export or share {feature} outputs in formats used by business teams.",
        f"The platform should retain query history, report configuration, or dashboard preferences where that improves repeated analysis.",
    ]


def _build_notification_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The system must trigger {feature} when the relevant business events or threshold conditions occur.",
        f"Users should be able to configure delivery channels, timing, or opt-in preferences related to {feature}.",
        f"{feature_title} must record delivery outcomes, retries, and failures for operational follow-up.",
        f"The interface should let authorized users review recent {feature} events and the current notification status.",
    ]


def _build_search_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"Users must be able to use {feature} to locate records quickly using relevant keywords, categories, or structured filters.",
        f"{feature_title} should support sorting, pagination, and clear empty-state behavior when no matching records are found.",
        f"The system must return results that reflect current access permissions and only expose data the requesting user is allowed to view.",
        f"Recent selections, saved filters, or contextual shortcuts should be supported where they improve repeated use of {feature}.",
    ]


def _build_integration_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The platform must support {feature} through stable service contracts with external systems or internal integration layers.",
        f"{feature_title} should validate inbound and outbound payloads before data is accepted or shared with downstream systems.",
        f"Failures, retries, and reconciliation outcomes for {feature} must be observable through logs, alerts, and operational dashboards.",
        f"Credentials, tokens, and connection settings used by {feature} must be managed securely and rotated according to policy.",
    ]


def _build_workflow_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"Authorized users must be able to create, update, and complete {feature} according to the approved business workflow.",
        f"The system should validate required fields, status transitions, and role-based actions before saving {feature} changes.",
        f"{feature_title} must maintain a clear history of assignments, approvals, or status updates for operational traceability.",
        f"The interface should surface the current workflow state, next available actions, and blocking conditions for {feature}.",
    ]


def _build_management_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The system must provide end-to-end {feature} capabilities for creating, updating, viewing, and retiring relevant business records.",
        f"{feature_title} should support role-based permissions, validation rules, and duplicate-prevention checks where appropriate.",
        f"Users must be able to search, filter, and review historical activity related to {feature} without leaving the module context.",
        f"The platform should maintain auditability for important actions performed within {feature} and retain operational history for reporting.",
    ]


def _build_tracking_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The system must capture {feature} data in real time or near real time as operational events occur.",
        f"{feature_title} should provide a timeline, status history, or change log so users can understand what happened and when.",
        f"Users must be able to review, filter, and reconcile {feature} records against the related business entities.",
        f"The platform should flag missing, inconsistent, or exception conditions that require attention during {feature}.",
    ]


def _build_default_requirements(feature_title):
    feature = _feature_slug(feature_title)
    return [
        f"The system must support {feature} as a complete business workflow within the application.",
        f"{feature_title} should validate required inputs, enforce role-based permissions, and prevent invalid state changes.",
        f"Users must be able to review the current state and recent activity associated with {feature} from the relevant module.",
        f"The platform should log significant actions, failures, and user-visible events related to {feature} for operational support.",
    ]


def build_realistic_requirements(feature_title):
    """Create more natural SRS requirement bullets from a feature title."""
    signals = feature_title.lower()

    if any(keyword in signals for keyword in ["authentication", "login", "registration", "identity", "verification", "account", "security", "access", "rbac", "encryption", "privacy", "fraud"]):
        return _build_auth_requirements(feature_title)
    if any(keyword in signals for keyword in ["report", "dashboard", "analytics", "kpi", "insight", "metric"]):
        return _build_reporting_requirements(feature_title)
    if any(keyword in signals for keyword in ["notification", "alert", "reminder"]):
        return _build_notification_requirements(feature_title)
    if any(keyword in signals for keyword in ["api", "integration", "sync", "import", "export", "gateway", "webhook", "feed"]):
        return _build_integration_requirements(feature_title)
    if any(keyword in signals for keyword in ["workflow", "approval", "automation", "booking", "checkout", "reservation", "order", "ticket", "appointment", "schedule", "assignment", "project", "task"]):
        return _build_workflow_requirements(feature_title)
    if any(keyword in signals for keyword in ["tracking", "monitoring", "history", "audit", "log", "reconciliation"]):
        return _build_tracking_requirements(feature_title)
    if any(keyword in signals for keyword in ["management", "portal", "profile", "payout", "payment", "payroll", "inventory", "supplier", "vendor", "asset", "document", "customer", "campaign", "attendance"]):
        return _build_management_requirements(feature_title)
    if any(keyword in signals for keyword in ["search", "catalog", "discovery", "browse", "wishlist", "filter"]):
        return _build_search_requirements(feature_title)
    return _build_default_requirements(feature_title)


def generate_simple_frs(fr_titles):
    """Generate FRs from a list of titles with realistic requirements only."""
    frs = {}
    for i, title in enumerate(fr_titles):
        fr_id = f"FR-{i+1:02d}"
        reqs = build_realistic_requirements(title)

        frs[fr_id] = {
            "title": title,
            "requirements": reqs,
        }

    return frs


def _clean_text_tree(value):
    """Strip lightweight markdown artifacts from parsed sample content."""
    if isinstance(value, dict):
        return {key: _clean_text_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_text_tree(item) for item in value]
    if isinstance(value, str):
        cleaned = value.replace("**", "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
    return value


CURATED_SAMPLE_OVERRIDES = {
    "01_ecommerce.json": {
        "title": "E-Commerce Platform",
        "technologies": ["Next.js", "Prisma", "MongoDB"],
        "actors": ["Customer", "Admin"],
    },
    "51_enterprise_erp.json": {
        "title": "Enterprise Resource Planning System",
        "technologies": ["React", "Node.js", "MongoDB", "Express"],
        "actors": ["Admin", "Manager", "Employee"],
    },
}


def create_sample_from_markdown(sample_filename, markdown_filename):
    """Create a sample JSON by parsing an authored markdown SRS."""
    markdown_path = PROJECT_ROOT / "samples" / markdown_filename
    parsed = _clean_text_tree(parse_srs(markdown_path.read_text(encoding="utf-8")).to_dict())
    parsed.update(CURATED_SAMPLE_OVERRIDES.get(sample_filename, {}))

    output = {}
    title = parsed.get("title", sample_filename)
    technologies = parsed.get("technologies", [])
    frs = parsed.get("functional_requirements", {})
    for fr_id, fr_data in frs.items():
        fr_data.pop("acceptance_criteria", None)
        output[fr_id] = generate_tasks_for_fr(
            fr_id,
            fr_data.get("title", fr_id),
            title,
            technologies,
            fr_data,
        )

    sample = {
        "input": parsed,
        "output": output,
    }

    output_dir = get_output_directory(sample_filename)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / sample_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  Created {sample_filename} from {markdown_filename}: {len(frs)} FRs")


def get_output_directory(sample_filename: str) -> Path:
    """Route generated dataset files into training or evaluation folders."""
    return EVALUATION_DIR if sample_filename.startswith("eval_") else TRAINING_DIR

def create_sample(filepath, title, techs, fr_titles):
    """Create a complete training sample file."""
    frs = generate_simple_frs(fr_titles)
    
    output = {}
    for fr_id in frs:
        output[fr_id] = generate_tasks_for_fr(fr_id, frs[fr_id]["title"], title, techs, frs[fr_id])
    
    sample = {
        "input": build_project_input(title, techs, frs),
        "output": output
    }
    
    with open(filepath, 'w', encoding="utf-8") as f:
        json.dump(sample, f, indent=2)
    
    print(f"  Created {os.path.basename(filepath)}: {len(fr_titles)} FRs")


def normalize_existing_sample_outputs(directory: Path):
    """Rewrite task outputs for existing samples using the current task template."""
    for sample_path in sorted(directory.glob("*.json")):
        with open(sample_path, "r", encoding="utf-8") as f:
            sample = json.load(f)

        project_input = sample.get("input", {})
        functional_requirements = project_input.get("functional_requirements", {})
        if not isinstance(functional_requirements, dict) or not functional_requirements:
            print(f"  Skipped {sample_path.name}: no functional requirements found")
            continue

        project_title = project_input.get("title", sample_path.stem)
        technologies = project_input.get("technologies", [])
        normalized_output = {}

        for fr_id, fr_data in functional_requirements.items():
            fr_payload = fr_data if isinstance(fr_data, dict) else {}
            normalized_output[fr_id] = generate_tasks_for_fr(
                fr_id,
                fr_payload.get("title", fr_id),
                project_title,
                technologies,
                fr_payload,
            )

        sample["output"] = normalized_output
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"  Normalized {sample_path.name}: {len(normalized_output)} FRs")


def main():
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    # Keep the holdout set clean and reproducible on every regeneration.
    for existing_eval_file in EVALUATION_DIR.glob("*.json"):
        existing_eval_file.unlink()

    curated_markdown_samples = [
        ("01_ecommerce.json", "sample_srs_ecommerce.md"),
        ("51_enterprise_erp.json", "sample_srs_erp.md"),
    ]

    for sample_filename, markdown_filename in curated_markdown_samples:
        create_sample_from_markdown(sample_filename, markdown_filename)
    
    # Process detailed domains (23, 24)
    for domain in DOMAINS:
        output_dir = get_output_directory(domain["file"])
        filepath = os.path.join(output_dir, domain["file"])
        fr_data = domain["frs"]
        
        frs = {}
        output = {}
        for i, (title, reqs, _acs) in enumerate(fr_data):
            fr_id = f"FR-{i+1:02d}"
            frs[fr_id] = {"title": title, "requirements": reqs}
            output[fr_id] = generate_tasks_for_fr(fr_id, title, domain["title"], domain["tech"], frs[fr_id])
        
        sample = {
            "input": build_project_input(domain["title"], domain["tech"], frs),
            "output": output
        }
        
        with open(filepath, 'w') as f:
            json.dump(sample, f, indent=2)
        print(f"  Created {domain['file']}: {len(fr_data)} FRs")
    
    # Process simple domains (25-40)
    for filename, title, techs, fr_titles in MORE_DOMAINS:
        output_dir = get_output_directory(filename)
        filepath = os.path.join(output_dir, filename)
        create_sample(filepath, title, techs, fr_titles)
    
    # Generate remaining domains (41-50) with unique topics
    extra_domains = [
        ("41_appointment.json", "Appointment Scheduling Platform", ["React", "Node.js", "PostgreSQL"],
         ["Business Registration", "Service Catalog Management", "Staff Profile and Availability", "Working Hours Configuration", "Break and Holiday Management", "Online Booking Widget", "Customer Self-booking", "Walk-in Management",
          "Appointment Calendar View", "Multi-staff Scheduling", "Recurring Appointment Support", "Group Appointment Booking", "Waitlist Management", "Buffer Time Between Appointments", "Appointment Confirmation", "Automated Reminders via SMS",
          "Email Reminder Notifications", "Reschedule and Cancellation", "No-show Tracking", "Customer Registration", "Customer Booking History", "Customer Notes and Preferences", "Payment at Booking", "Package and Membership Sales",
          "Gift Certificate Management", "Intake Form Builder", "Pre-appointment Questionnaire", "Review and Rating Collection", "Revenue and Booking Reports", "Staff Performance Reports", "Customer Retention Analysis", "Multi-location Support",
          "Branded Booking Page", "Website Widget Integration", "Google Calendar Sync", "Zapier Integration", "Mobile App for Customers", "Staff Mobile App", "Admin Dashboard", "Two-way SMS Communication"]),
        ("42_document_mgmt.json", "Document Management System", ["React", "Java Spring Boot", "PostgreSQL", "Elasticsearch"],
         ["Document Upload and Storage", "Folder and Directory Structure", "Document Versioning", "Check-in and Check-out", "Document Search Full-text", "Metadata and Tag Management", "Document Preview", "Document Download",
          "Access Control per Document", "Role-based Permissions", "Share Document via Link", "Collaborative Editing", "Comment and Annotation", "Approval Workflow", "Digital Signature Integration", "Document Template Management",
          "Bulk Upload and Import", "OCR Text Extraction", "Document Classification", "Retention Policy Management", "Archive and Purge Scheduling", "Audit Trail", "Activity Log per Document", "Notification on Document Changes",
          "Email Integration for Upload", "Document Comparison", "Redaction Tool", "Watermark Application", "Print Management", "Mobile Access", "Offline Sync", "Trash and Recovery", "Storage Quota Management",
          "Compliance Reporting", "Custom Metadata Fields", "Saved Search Queries", "Dashboard and Analytics", "API for Integration", "SSO Authentication", "Multi-language Support"]),
        ("43_recipe_cooking.json", "Recipe and Cooking Application", ["React Native", "Node.js", "MongoDB"],
         ["User Registration and Profile", "Recipe Browsing by Category", "Recipe Search with Ingredients", "Recipe Detail with Steps", "Photo and Video for Recipes", "Cooking Timer Integration", "Ingredient Quantity Scaling",
          "Nutritional Information Display", "Dietary Filter", "Allergen Warning Display", "Shopping List Generation", "Pantry Inventory Tracking", "Meal Planning Calendar", "Weekly Meal Plan Generator", "Recipe Rating and Review",
          "Recipe Collection and Bookmarks", "User Recipe Submission", "Recipe Moderation", "Step-by-step Cooking Mode", "Voice-guided Cooking", "Social Sharing of Recipes", "Follow Other Cooks", "Activity Feed",
          "Cooking Challenge Events", "Seasonal Recipe Collections", "Wine Pairing Suggestions", "Substitution Suggestions", "Cost Estimation per Recipe", "Cooking Skill Level Tagging", "Video Tutorial Integration",
          "Podcast Integration", "Chef Profile Pages", "Local Ingredient Sourcing", "Push Notifications", "Offline Recipe Access", "Admin Content Management", "Analytics Dashboard", "Multi-language Recipes"]),
        ("44_sports_league.json", "Sports League Management", ["React", "Node.js", "PostgreSQL"],
         ["League and Season Creation", "Team Registration", "Player Registration and Roster", "Division and Conference Setup", "Schedule Generation Algorithm", "Fixture Management", "Venue and Field Management", "Referee Assignment",
          "Live Score Entry", "Game Statistics Recording", "Player Statistics Tracking", "Team Standing Calculations", "Playoff Bracket Generation", "Championship Tracking", "Player Transfer System", "Injury Report Management",
          "Suspension and Discipline Tracking", "Team Messaging and Communication", "Fan Registration", "Live Score Board for Fans", "News and Announcement Publishing", "Photo Gallery per Game", "Video Highlight Upload",
          "Merchandise Store Integration", "Ticket Sales for Games", "Season Pass Management", "Sponsorship Management", "Financial Tracking per Team", "Registration Fee Collection", "Waiver and Consent Management",
          "Mobile App for Scorekeeper", "Parent Portal for Youth Leagues", "Coach Portal", "Analytics and Performance Reports", "League Comparison Year over Year", "Custom Award and MVP Voting", "Social Media Integration",
          "API for External Stats Sites", "Admin Dashboard", "Multi-sport Support"]),
        ("45_personal_finance.json", "Personal Finance and Budgeting App", ["React Native", "Node.js", "PostgreSQL"],
         ["User Registration and Security", "Bank Account Linking", "Credit Card Account Linking", "Transaction Auto-import", "Manual Transaction Entry", "Transaction Categorization", "Custom Category Creation", "Budget Creation per Category",
          "Budget vs Actual Tracking", "Spending Alerts at Threshold", "Income Tracking", "Recurring Transaction Setup", "Bill Reminder with Due Dates", "Bill Payment Tracking", "Savings Goal Setting", "Savings Progress Tracking",
          "Net Worth Calculation", "Net Worth History Chart", "Debt Tracking and Payoff Plan", "Debt Snowball Calculator", "Investment Portfolio Tracking", "Stock and Crypto Price Updates", "Dividend Tracking", "Tax Category Tagging",
          "Annual Tax Summary Report", "Cash Flow Forecast", "Monthly Financial Report", "Spending Trend Analysis", "Category Comparison Month over Month", "Shared Budget with Partner", "Family Account Support", "Receipt Photo Attachment",
          "Export to CSV and PDF", "Financial Goal Milestones", "Currency Conversion", "Multi-currency Account Support", "Push Notification for Bills and Budgets", "Biometric App Lock", "Data Encryption", "Admin Analytics"]),
        ("46_digital_marketplace.json", "Digital Product Marketplace", ["Next.js", "Node.js", "PostgreSQL", "S3"],
         ["Creator Registration and Verification", "Digital Product Upload", "Product Preview Generation", "License Type Management", "Pricing Tiers and Bundles", "Free Product Listing", "Product Search and Discovery", "Category Browsing",
          "Tag-based Filtering", "Product Detail Page", "Live Preview for Themes and Templates", "Customer Registration", "Shopping Cart", "Checkout and Payment", "Instant Digital Download", "License Key Generation",
          "Download Link Expiry Management", "Customer Download History", "Product Rating and Review", "Creator Storefront Page", "Creator Analytics Dashboard", "Revenue and Sales Reports", "Commission and Fee Management", "Creator Payout Processing",
          "Affiliate Program", "Discount Coupon System", "Bundle Deal Creation", "Featured Product Promotion", "Wishlist and Favorites", "Customer Support Tickets", "Refund Policy and Processing", "Copyright Claim System",
          "DMCA Takedown Process", "Content Quality Review", "Admin Approval for Products", "Platform Analytics", "Email Marketing Integration", "Social Media Sharing", "API for Partners", "Multi-currency Support"]),
        ("47_parking.json", "Smart Parking Management System", ["React", "Node.js", "PostgreSQL", "IoT"],
         ["Parking Facility Registration", "Parking Zone and Floor Configuration", "Individual Spot Management", "Sensor Integration for Occupancy", "Real-time Availability Display", "Customer Registration", "Vehicle Registration",
          "Find Nearby Parking", "Map View with Available Spots", "Advance Reservation Booking", "QR Code Entry and Exit", "License Plate Recognition", "Automated Barrier Control", "Parking Duration Tracking", "Dynamic Pricing by Demand",
          "Hourly and Daily Rate Configuration", "Monthly Pass Management", "Corporate Account Management", "Payment Processing", "Contactless Payment", "Invoice and Receipt Generation", "Overstay Alerts", "Violation Management",
          "EV Charging Spot Management", "Disabled Parking Management", "Valet Parking Request", "Parking Navigation to Spot", "In-app Spot Finder Map", "Push Notification for Expiry", "Revenue and Occupancy Reports",
          "Peak Hour Analytics", "Turnover Rate Reports", "Customer Loyalty Program", "Multi-facility Dashboard", "Staff Mobile App", "Admin Configuration Panel", "API for City Integration", "Data Export"]),
        ("48_charity.json", "Charity and Donation Platform", ["React", "Node.js", "PostgreSQL", "Stripe"],
         ["Charity Organization Registration", "Organization Verification", "Campaign Creation with Goal", "Campaign Media and Story", "Donation Page Customization", "One-time Donation Processing", "Recurring Donation Setup", "Peer-to-peer Fundraising",
          "Team Fundraising Pages", "Donor Registration", "Anonymous Donation Option", "Donation Receipt Generation", "Tax-deductible Receipt", "Gift Aid Declaration", "In Memory and In Honor Donations", "Corporate Matching Gifts",
          "Event-based Fundraising", "Auction and Raffle Integration", "Merchandise Sales for Charity", "Donor Management CRM", "Donor Communication", "Email Thank You Automation", "Impact Report Generation", "Fund Allocation Tracking",
          "Expense Tracking per Campaign", "Volunteer Coordination", "Grant Application Management", "Grant Reporting", "Social Media Fundraising", "Facebook and Instagram Integration", "Campaign Sharing Widgets", "Embeddable Donation Button",
          "Mobile Donation App", "Text-to-Donate", "Analytics and Insights Dashboard", "Donor Retention Analysis", "Campaign Performance Reports", "Admin Platform Management", "Compliance and Audit Reports", "Multi-currency Donations"]),
        ("49_pet_care.json", "Pet Care and Veterinary Platform", ["React Native", "Node.js", "MongoDB"],
         ["Pet Owner Registration", "Pet Profile Creation", "Multiple Pet Support", "Vaccination Record Tracking", "Medication Schedule and Reminders", "Vet Clinic Registration", "Vet Doctor Profiles", "Appointment Booking with Vet",
          "Video Consultation", "Walk-in Queue for Clinics", "Medical History and Records", "Lab Result Tracking", "Prescription Management", "Pet Insurance Integration", "Grooming Service Booking", "Boarding and Daycare Booking",
          "Dog Walking Service", "Pet Sitting Marketplace", "Pet Adoption Listings", "Pet Lost and Found Board", "Pet Food and Supply Store", "Auto-reorder Pet Supplies", "Pet Activity and Exercise Tracking", "Weight and Growth Charts",
          "Breed Information Database", "Training Tips and Resources", "Community Forum for Pet Owners", "Pet Photo Social Feed", "Reviews for Vets and Services", "Emergency Vet Locator", "Pet First Aid Guides", "Multi-pet Family Dashboard",
          "Billing and Payment", "Push Notification Reminders", "Admin Dashboard", "Analytics and Reports"]),
        ("50_construction.json", "Construction Project Management", ["React", "Node.js", "PostgreSQL"],
         ["Project Registration and Setup", "Site Information Management", "Stakeholder and Contact Management", "Project Phase and Milestone Tracking", "Gantt Chart Scheduling", "Task Assignment and Tracking", "Daily Log and Site Diary",
          "Weather Delay Tracking", "Resource Allocation", "Labor Hour Tracking", "Equipment Tracking and Assignment", "Material Requisition", "Material Delivery Tracking", "Inventory Management on Site", "Subcontractor Management",
          "Subcontractor Bidding Process", "Contract Management", "Change Order Management", "Budget and Cost Tracking", "Invoice and Payment Processing", "Progress Billing", "Lien Waiver Management", "RFI Management",
          "Submittal Tracking", "Punch List Creation", "Inspection Scheduling", "Quality Assurance Checklists", "Safety Incident Reporting", "Safety Training Tracking", "OSHA Compliance Checklist", "Drawing and Blueprint Management",
          "3D Model Viewer Integration", "Photo and Video Documentation", "Time-lapse Camera Integration", "Client Portal with Progress", "Permit and License Tracking", "Warranty Tracking", "Asset Handover Documentation",
          "Analytics and Project Reports", "Multi-project Dashboard"]),
    ]

    for filename, title, techs, fr_titles in extra_domains:
        output_dir = get_output_directory(filename)
        filepath = os.path.join(output_dir, filename)
        create_sample(filepath, title, techs, fr_titles)

    evaluation_domains = [
        (
            "eval_01_security_operations.json",
            "Security Operations and Incident Response Platform",
            ["React", "Python FastAPI", "PostgreSQL", "Redis"],
            [
                "Security Alert Ingestion",
                "Incident Case Creation",
                "Severity Classification Workflow",
                "Analyst Assignment Queue",
                "Investigation Timeline Tracking",
                "Evidence Attachment Repository",
                "Indicator of Compromise Management",
                "Containment Action Approval",
                "Endpoint Isolation Request Workflow",
                "Threat Intelligence Feed Correlation",
                "SLA Breach Alerting",
                "Executive Incident Summary Dashboard",
                "Root Cause Documentation",
                "Post-incident Review Tracking",
                "Audit-ready Incident Export",
                "Role-based Access for Security Teams",
                "Secure Notification Escalation",
                "Playbook Runbook Catalog",
            ],
        ),
        (
            "eval_02_lease_administration.json",
            "Commercial Lease Administration Platform",
            ["Next.js", "Node.js", "PostgreSQL", "Elasticsearch"],
            [
                "Property Portfolio Registration",
                "Tenant Organization Onboarding",
                "Lease Abstract Data Capture",
                "Rent Schedule Management",
                "Escalation Clause Tracking",
                "Security Deposit Monitoring",
                "Lease Document Repository",
                "Renewal Notice Automation",
                "Critical Date Calendar",
                "Maintenance Charge Allocation",
                "Invoice Generation for Tenants",
                "Payment Reconciliation",
                "Vacancy and Occupancy Dashboard",
                "Amendment Version Tracking",
                "Landlord Approval Workflow",
                "Broker Commission Tracking",
                "Portfolio Reporting for Finance",
                "Audit Trail for Lease Changes",
            ],
        ),
        (
            "eval_03_pharmacy_management.json",
            "Pharmacy Dispensing and Inventory Control System",
            ["React", "Java Spring Boot", "PostgreSQL"],
            [
                "Prescription Intake and Validation",
                "Patient Medication Profile Lookup",
                "Drug Interaction Alerting",
                "Controlled Substance Verification",
                "Dispensing Queue Management",
                "Barcode-based Medication Picking",
                "Batch and Expiry Tracking",
                "Inventory Reorder Thresholds",
                "Supplier Purchase Order Creation",
                "Cold Storage Temperature Logging",
                "Prescription Refill Request Workflow",
                "Insurance Claim Submission",
                "Cash and Card Billing",
                "Pharmacist Verification Step",
                "Rejected Claim Resolution",
                "Daily Dispensing Summary Report",
                "Medication Recall Handling",
                "User Permission Segmentation",
            ],
        ),
        (
            "eval_04_grant_management.json",
            "Grant Management and Funding Operations Platform",
            ["React", "Python Django", "PostgreSQL", "Redis"],
            [
                "Funding Opportunity Publishing",
                "Applicant Organization Registration",
                "Eligibility Screening Workflow",
                "Grant Application Submission",
                "Narrative Section Authoring",
                "Budget Workbook Management",
                "Supporting Document Upload",
                "Reviewer Assignment",
                "Scoring Rubric Configuration",
                "Reviewer Conflict of Interest Declaration",
                "Evaluation Committee Dashboard",
                "Award Recommendation Workflow",
                "Award Letter Generation",
                "Grant Agreement Tracking",
                "Milestone-based Disbursement Scheduling",
                "Beneficiary Progress Reporting",
                "Budget Utilization Monitoring",
                "Site Visit Planning",
                "Risk Flag and Escalation Tracking",
                "Impact Metrics Dashboard",
                "Audit Evidence Repository",
                "Grant Closeout Checklist",
                "Portfolio Reporting for Leadership",
                "Email Notification Automation",
            ],
        ),
        (
            "eval_05_manufacturing_quality.json",
            "Manufacturing Quality and Inspection Management System",
            ["React", "Node.js", "PostgreSQL", "TimescaleDB"],
            [
                "Plant and Production Line Setup",
                "Inspection Plan Definition",
                "Incoming Material Quality Checks",
                "In-process Inspection Recording",
                "Final Product Inspection Workflow",
                "Defect Classification Catalog",
                "Corrective Action Request Management",
                "Non-conformance Case Tracking",
                "Root Cause Analysis Workspace",
                "Supplier Quality Scorecards",
                "Calibration Schedule Tracking",
                "Sampling Rule Configuration",
                "Batch Traceability Lookup",
                "Photo Evidence Capture",
                "Quality Hold and Release Workflow",
                "Rework Order Tracking",
                "Regulatory Compliance Checklist",
                "Shift Quality Dashboard",
                "Scrap and Yield Reporting",
                "Audit Preparation Reports",
            ],
        ),
        (
            "eval_06_membership_association.json",
            "Membership and Association Management Portal",
            ["Next.js", "Node.js", "PostgreSQL", "Stripe"],
            [
                "Member Registration and Profile Management",
                "Membership Tier Configuration",
                "Application Review and Approval",
                "Renewal Reminder Automation",
                "Online Membership Payment",
                "Corporate Membership Accounts",
                "Member Directory Search",
                "Committee and Chapter Management",
                "Event Registration for Members",
                "Continuing Education Credit Tracking",
                "Certificate Issuance",
                "Document Library Access Control",
                "Announcement and Newsletter Publishing",
                "Volunteer Signup Workflow",
                "Member Support Ticketing",
                "Benefits Redemption Tracking",
                "Sponsor Management",
                "Board Reporting Dashboard",
            ],
        ),
    ]

    for filename, title, techs, fr_titles in evaluation_domains:
        filepath = os.path.join(EVALUATION_DIR, filename)
        create_sample(filepath, title, techs, fr_titles)

    normalize_existing_sample_outputs(TRAINING_DIR)
    normalize_existing_sample_outputs(EVALUATION_DIR)

    training_total = len(list(TRAINING_DIR.glob("*.json")))
    evaluation_total = len(list(EVALUATION_DIR.glob("*.json")))
    print(
        f"\n  Generated {training_total} training files and "
        f"{evaluation_total} evaluation files"
    )


if __name__ == "__main__":
    main()
