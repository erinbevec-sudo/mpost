INSERT INTO users (email, display_name)
VALUES
  ('user@example.com', 'Demo User'),
  ('chief@example.com', 'Demo Chief of Staff'),
  ('admin@example.com', 'Demo RBAC Admin')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'user'
WHERE u.email = 'user@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'chief_of_staff'
WHERE u.email = 'chief@example.com'
ON CONFLICT DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'rbac_admin'
WHERE u.email = 'admin@example.com'
ON CONFLICT DO NOTHING;
