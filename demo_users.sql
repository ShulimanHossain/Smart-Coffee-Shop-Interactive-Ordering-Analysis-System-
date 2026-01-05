-- Demo User Inserts for Cafe ML Database
-- This file contains sample INSERT statements for the User table
-- User codes follow the pattern: role + 2-digit number (e.g., admin01, manager01)

USE Cafe_ML;

-- Insert Admin Users
INSERT INTO User (user_code, name, email, password, role) VALUES
('admin01', 'John Admin', 'admin01@cafeml.com', 'admin123', 'admin'),
('admin02', 'Sarah Admin', 'admin02@cafeml.com', 'admin456', 'admin'),
('admin03', 'Mike Admin', 'admin03@cafeml.com', 'admin789', 'admin');

-- Insert Manager Users
INSERT INTO User (user_code, name, email, password, role) VALUES
('manager01', 'Emily Manager', 'manager01@cafeml.com', 'manager123', 'manager'),
('manager02', 'David Manager', 'manager02@cafeml.com', 'manager456', 'manager'),
('manager03', 'Lisa Manager', 'manager03@cafeml.com', 'manager789', 'manager');

-- Insert Staff Users (if needed)
INSERT INTO User (user_code, name, email, password, role) VALUES
('staff01', 'Tom Staff', 'staff01@cafeml.com', 'staff123', 'staff'),
('staff02', 'Anna Staff', 'staff02@cafeml.com', 'staff456', 'staff');

-- Note: The user_code format is:
-- - admin01, admin02, admin03... for admins
-- - manager01, manager02, manager03... for managers  
-- - staff01, staff02, staff03... for staff
-- The last 2 digits increment automatically based on existing users of that role

-- To verify the inserts:
-- SELECT * FROM User ORDER BY role, user_code;

