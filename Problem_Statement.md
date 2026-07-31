# Problem Statement

## 1. Title
Vehicle Tracking and Fleet Monitoring Platform

## 2. Domain
Transportation / Logistics / IoT

## 3. Who is the user?

There are three main types of users for this system:

- **Fleet Manager** - Someone who owns or operates a fleet of vehicles (trucks, delivery vans, company cars). They want to see where every vehicle is, how it's being driven, and get alerts when something needs attention. This is the primary user type.
- **Driver** - The person behind the wheel. They get route suggestions, driving score feedback, and can report issues through the mobile app.
- **Mechanic / Maintenance Coordinator** - Handles vehicle servicing and repairs. Gets notified about predictive maintenance based on driving patterns and vehicle health data.

## 4. What problem are we solving?

Managing a fleet of vehicles is a nightmare when you're flying blind. Right now, most small-to-midsize fleet operators rely on spreadsheets, phone calls, and gut feelings. They don't know if a driver is speeding or idling too long. They find out about maintenance problems when the vehicle breaks down on the highway, which means expensive towing, missed deliveries, and angry customers. There's no central place to see route history, driver behavior, or maintenance schedules. This platform brings real-time tracking, route optimization, and predictive maintenance into one dashboard so fleet managers can actually manage instead of guessing.

## 5. Proposed Solution

What the application will do:

- **Real-time GPS tracking** - Vehicles send location pings to the backend every 30 seconds, which get displayed on an interactive map in the web dashboard
- **Route history and replay** - View past trips on a map, with speed and stoppage data for each vehicle
- **Driver behavior scoring** - Each trip gets a score based on harsh braking, speeding, and rapid acceleration. Drivers can see their own scores.
- **Basic route optimization** - For multi-stop delivery runs, the system can suggest the most efficient order based on distance and time estimates
- **Maintenance scheduler** - Tracks vehicle mileage and driving patterns to flag when service is due
- **Alert system** - Email/SMS notifications for speeding, geofence breaches, low battery on GPS device, and upcoming maintenance
- **Admin dashboard** - Fleet managers can add/remove vehicles, assign drivers, view reports, and set up geofences
- **Mobile-responsive frontend** - Works on both desktop and mobile so drivers and managers can check in from anywhere

## 6. Core Entities / Database Tables

1. **users** - id, name, email, password_hash, role (manager/driver/mechanic), created_at
2. **vehicles** - id, fleet_id, license_plate, make, model, year, vin, status (active/inactive/repair), current_mileage, created_at
3. **locations** - id, vehicle_id, latitude, longitude, speed, timestamp, ignition_status
4. **routes** - id, vehicle_id, driver_id, start_time, end_time, start_location, end_location, distance_km, status (planned/in-progress/completed)
5. **route_stops** - id, route_id, sequence, latitude, longitude, address, planned_arrival, actual_arrival, status (pending/arrived/skipped)
6. **maintenance_records** - id, vehicle_id, odometer_reading, service_type, description, cost, scheduled_date, completed_date, status
7. **alerts** - id, vehicle_id, driver_id, type (speeding/geofence/maintenance/battery), message, severity, timestamp, acknowledged
8. **geofences** - id, name, center_lat, center_lng, radius_meters, created_by, vehicle_id (optional - applies to all if null)

## 7. User Roles & Permissions

| Role | Can do what |
|:-----|:------------|
| **Admin / Fleet Manager** | Full access - add vehicles, assign drivers, view all data, create geofences, see all alerts, generate reports |
| **Driver** | View own assigned vehicle and routes, see driving score, receive alerts, mark stops as complete, report issues |
| **Mechanic** | View maintenance records and schedules, update service status, see vehicle health data |

## 8. Success Criteria

- A driver can open the mobile app and see their assigned route with stops plotted on a map
- A fleet manager can open the dashboard and see all vehicles plotted on a single map in real-time
- Drivers get notified (email/SMS) when they exceed the speed limit by more than 10 mph in a geofenced area
- The system can generate an optimized route when a manager enters 5+ delivery stops
- A maintenance alert pops up on the mechanic's dashboard 7 days before a vehicle is due for service
- The whole thing runs on a live URL - not just on a laptop

## 9. Out of Scope

- Actual hardware GPS device integration (we'll simulate location data with a mock script for now)
- Native mobile app (going responsive web only for this semester)
- AI route optimization with live traffic data (we'll do a basic distance-based optimization)
- The predictive maintenance model itself (that's the enhancement feature for Day 41-60)
- Multi-company / multi-tenant support (one fleet per deployment for now)

## 10. Chosen Track

Python (FastAPI)
