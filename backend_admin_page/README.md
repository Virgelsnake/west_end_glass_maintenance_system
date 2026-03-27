# West End Glass Admin Dashboard

React + Vite frontend for managing the West End Glass Maintenance System. Administrators use this dashboard to create tickets, manage technicians and machines, view audit logs, and monitor system activity.

## Features

- **Ticket Management:** Create, edit, assign, and close maintenance tickets
- **User Management:** Register technicians, manage PIN-based authentication
- **Machine Registry:** Register machines with NFC tag support
- **Audit Trail:** View all system events with actor, timestamp, and details
- **Dashboard:** Real-time KPIs (open tickets, overdue, technician workload)
- **Role-Based Access:** Super Admin, Editor, and Viewer roles with permission controls

## Quick Start

### 1. Install Dependencies

```bash
cd backend_admin_page
npm install
```

### 2. Development Server

```bash
npm run dev
```

Runs at: http://localhost:5173

### 3. Build for Production

```bash
npm run build
```

### 4. Preview Production Build

```bash
npm run preview
```

## Configuration

### API Endpoint

The dashboard connects to the backend API. By default it uses `http://localhost:8000`.

To change, update in `src/api/client.js`:

```javascript
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';
```

Or set via environment variable:

```bash
VITE_API_URL=http://your-api-server:8000 npm run dev
```

### Authentication

1. **Login Page** (`src/pages/Login.jsx`)
   - Username + password (admin credentials from backend `.env`)
   - JWT token stored in localStorage
   - Auto-redirects to dashboard on success

2. **Protected Routes** (`src/components/ProtectedRoute.jsx`)
   - Routes check for valid JWT token
   - Redirects to login if token missing or expired
   - Validates role-based permissions

## Directory Structure

```
backend_admin_page/
├── src/
│   ├── main.jsx               # Entry point
│   ├── App.jsx                # Main layout with routes
│   ├── App.css                # Global styles
│   ├── index.css              # Base styles
│   ├── api/
│   │   └── client.js          # Axios instance with auth headers
│   ├── context/
│   │   └── AuthContext.jsx    # Login state & JWT management
│   ├── components/
│   │   ├── Navbar.jsx         # Top navigation
│   │   ├── ProtectedRoute.jsx # Auth guard for routes
│   │   ├── ConversationView.jsx
│   │   ├── PhotoGallery.jsx
│   │   ├── StepList.jsx
│   │   └── ...
│   ├── pages/
│   │   ├── Login.jsx          # /login
│   │   ├── Dashboard.jsx      # / (KPIs, stats)
│   │   ├── Tickets.jsx        # /tickets (list & creation)
│   │   ├── TicketDetail.jsx   # /tickets/:id (single ticket)
│   │   ├── Users.jsx          # /users (technician management)
│   │   ├── Machines.jsx       # /machines (machine registry)
│   │   ├── AuditLog.jsx       # /audit (event log)
│   │   └── ...
│   └── assets/
├── public/
│   └── (static files)
├── index.html
├── vite.config.js
├── eslint.config.js
├── package.json
└── README.md (this file)
```

## Pages & Functionality

### Dashboard (`/`)

Real-time overview of system status:
- **Ticket Counts:** Open, in_progress, closed
- **Overdue Tickets:** Count and list
- **Technician Workload:** Assignments per tech
- **Activity Feed:** Recent audit logs

### Tickets (`/tickets`)

Manage all maintenance work:
- **List View:** Filter by status, machine, technician
- **Create Ticket:** Form with steps builder
- **Edit Ticket:** Reassign, update priority, add notes
- **View Details:** See full conversation, steps, photos
- **Actions:** Close, reassign, bulk operations

### Users (`/users`)

Manage field technicians:
- **List:** All users with status
- **Create:** Add new technician (phone, name, language)
- **Edit:** Update details, set/change PIN
- **Deactivate:** Remove from active rotation
- **Actions:** Reset PIN, view activity

### Machines (`/machines`)

Machine registry for NFC tags:
- **List:** All registered machines
- **Create:** Register new machine (ID, name, location)
- **Edit:** Update machine details
- **NFC Tags:** Generate deep links for tag encoding
- **QR Codes:** Scannable URLs for machines

### Audit Log (`/audit`)

Comprehensive event history:
- **Timeline:** All system events in chronological order
- **Filter:** By actor, event type, machine, ticket
- **Details:** Full payload and context for each event
- **Export:** Download audit trail for compliance

## Development

### Component Pattern

```javascript
// Functional components with hooks
import { useState, useCallback } from "react";
import client from "../api/client";

export default function MyPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await client.get("/endpoint");
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  // useEffect for initial load
  // render...
}
```

### Styling

- **Tailwind CSS** for utility classes
- **Amber color scheme** (primary: amber-500,600)
- **Responsive design** with mobile-first approach
- **Lucide icons** for consistent iconography

### Making API Calls

```javascript
import client from "../api/client";

// GET request (auto-includes JWT from localStorage)
const res = await client.get("/tickets");

// POST request with data
const res = await client.post("/tickets", {
  machine_id: "WEG-MACHINE-0042",
  title: "Maintenance",
});

// PATCH request (partial update)
const res = await client.patch("/tickets/id", { status: "closed" });

// Handle errors
try {
  await client.post("/tickets", payload);
} catch (err) {
  const errorMsg = err.response?.data?.detail || "Failed to create";
  console.error(errorMsg);
}
```

### Authentication

Login is handled via `AuthContext`:

```javascript
import { useContext } from "react";
import { AuthContext } from "../context/AuthContext";

export default function MyComponent() {
  const auth = useContext(AuthContext);
  const { user, logout } = auth;

  // Use auth.user for current user info
  // Use logout() to exit
}
```

## Testing

### Via Admin Dashboard UI

1. Start all services: `docker compose up -d`
2. Navigate to http://localhost:3030
3. Login with default admin credentials
4. Create test data and verify operations

### Via CLI Simulator (Technician Side)

While testing the dashboard, also test the technician bot:

```bash
python ../tools/simulate_chat.py
```

This lets you see how technicians interact with tickets you create.

## TypeScript Migration

Currently uses JavaScript. To add TypeScript:

1. Rename `.jsx` files to `.tsx`, `.js` to `.ts`
2. Add type annotations
3. Use `typescript-eslint` for linting
4. Update `tsconfig.json`

See [Vite + TypeScript Guide](https://vitejs.dev/guide/features.html#typescript)

## Build & Deployment

### Development

```bash
npm run dev
```

### Production Build

```bash
npm run build
```

Outputs to `dist/` directory.

### Docker Build

```bash
docker build -t west-end-glass-admin:latest .
```

### Environment Variables for Docker

```dockerfile
ENV VITE_API_URL=http://api:8000
```

## Performance Considerations

- **Pagination:** Ticket and message lists are paginated
- **Lazy Loading:** Images in photo galleries load on demand
- **Memoization:** Components use React.memo and useCallback where appropriate
- **Code Splitting:** Routes are lazy-loaded where possible

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard won't load | Check backend is running at http://localhost:8000/health |
| Login fails | Verify username/password in backend `.env` |
| API calls fail | Check browser DevTools → Network tab for 401/403 errors |
| Styling looks broken | Run `npm install` to ensure Tailwind CSS is present |
| Hot reload not working | Restart dev server: `npm run dev` |

## Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Lucide Icons](https://lucide.dev/)
- [Axios](https://axios-http.com/)

## Related Documentation

- [Backend API](../backend_api/README.md) — API endpoints and setup
- [Quick Start Guide](../QUICKSTART.md) — Full system setup
- [Testing Guide](../TESTING.md) — Development workflows
- [Tools Documentation](../tools/README.md) — CLI simulator and testing tools
