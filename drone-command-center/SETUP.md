# MJN Drone OS — Complete Setup & Installation Guide

## Prerequisites

### 1. Install Node.js (v18 or higher)

**Download:** https://nodejs.org/ (Download LTS version)

Verify installation:

```bash
node --version
# Should output: v18.x.x or higher (e.g. v20.11.0)

npm --version
# Should output: 9.x.x or higher (e.g. 10.8.0)
```

If `node` is not found:
- **Windows:** Download the installer from nodejs.org and run it. Restart your terminal.
- **macOS:** `brew install node`
- **Linux:** `sudo apt install nodejs npm`

### 2. Install Git

**Download:** https://git-scm.com/downloads

Verify:

```bash
git --version
# Should output: git version 2.x.x
```

### 3. Install Python (v3.10 or higher — optional, for backend)

**Download:** https://www.python.org/downloads/

**IMPORTANT (Windows):** During installation, **check "Add Python to PATH"**.

Verify:

```bash
python --version
# Should output: Python 3.10.x or higher
```

---

## Step-by-Step Setup

### Step 1: Clone the Repository

Open a **new terminal** (Command Prompt, PowerShell, or Terminal):

```bash
git clone https://github.com/sherly7Veronica/MJN.git
```

This creates a folder called `MJN`. Navigate into it:

```bash
cd MJN
```

---

### Step 2: Navigate to the Frontend Directory

```bash
cd drone-command-center
```

**Verify you're in the right place:**

```bash
pwd      # macOS/Linux
echo %cd%   # Windows Command Prompt
Get-Location # Windows PowerShell
```

Expected output: `.../MJN/drone-command-center`

You should see files like `package.json`, `next.config.ts`, `tsconfig.json`.

---

### Step 3: Install Frontend Dependencies

```bash
npm install
```

This will download and install all required packages:

| Package | Purpose |
|---------|---------|
| `next` | React framework |
| `react` / `react-dom` | UI library |
| `leaflet` | GIS map engine |
| `@types/leaflet` | TypeScript types for Leaflet |
| `zustand` | State management |
| `lucide-react` | Icons |
| `typescript` | TypeScript compiler |

**Expected output:**

```
added 1234 packages in 45s
```

If you see `npm ERR!`:
- Check your internet connection
- Try `npm cache clean --force && npm install`
- Ensure Node.js v18+ is installed (`node --version`)

---

### Step 4: Run the Frontend (Development Mode)

```bash
npm run dev
```

**Expected output:**

```
▲ Next.js 16.2.9 (Turbopack)
- Local: http://localhost:3000
- Network: http://192.168.x.x:3000
✓ Ready in ~2s
```

**Keep this terminal running.** The dev server will automatically reload when you make changes.

---

### Step 5: Open the Dashboard

Open your browser and go to:

```
http://localhost:3000
```

You should see the MJN Drone OS dashboard with:
- A **Leaflet map** centered on Bangalore (lat: 12.9716, lng: 77.5946)
- A **drone marker** (cyan icon with heading arrow) moving along a mission
- **Waypoints** (violet home icon, red destination icon, numbered waypoint markers)
- **Path layers** (green visited path, orange active segment, blue planned route)
- **Left panel** showing: Drone ID, Status, Speed, Altitude, Battery (with bar), GPS, Signal, System, Weather
- **Right panel** showing: Mission ID, Progress, ETA, Planner Decision, Waypoint info, Predictions, AI Panel
- **AI Panel** with navigation engine, prediction engine, decision engine, sensor fusion, obstacle count
- **Bottom bar**: Attitude indicator, Compass, ALT, SPD, V/S, Signal bar, Battery bar
- **UTC clock** in the top-right header

---

### Step 6: Production Build (Optional)

If you want to build for production:

```bash
npm run build
```

**Expected output:**

```
✓ Compiled successfully
✓ TypeScript passed
✓ Static pages generated
✓ Final optimization complete
```

Then start the production server:

```bash
npm start
```

---

## Python Backend Setup (Optional)

The frontend runs a built-in simulation engine by default (no backend required). To also run the Python backend:

### Step 1: Navigate to Project Root

Open a **new terminal** and go to the project root:

```bash
cd MJN
```

### Step 2: Create a Virtual Environment

**Windows (Command Prompt or PowerShell):**

```bash
python -m venv venv
```

**macOS / Linux:**

```bash
python3 -m venv venv
```

This creates a `venv/` folder with an isolated Python environment.

### Step 3: Activate the Virtual Environment

**Windows (Command Prompt):**

```bash
venv\Scripts\activate
```

**Windows (PowerShell):**

```powershell
venv\Scripts\Activate.ps1
```

If PowerShell gives a security error, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again.

**macOS / Linux:**

```bash
source venv/bin/activate
```

**Verify activation:**

```bash
# You should see (venv) at the beginning of your terminal prompt
(venv) C:\Users\...\MJN>
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `numpy` | Numerical computation |
| `opencv-python` | Computer vision |
| `pillow` | Image processing |
| `matplotlib` | Plotting |
| `shapely` | Geometry operations |
| `pyproj` | Coordinate transformations |
| `utm` | UTM coordinate conversion |
| `latlon` | Geographic calculations |

**If `pip` is not found, use:**

```bash
python -m pip install -r requirements.txt
```

### Step 5: Run the Python Backend

```bash
python main.py
```

**Expected output:**

```
[INFO] MJN Drone OS - Backend Starting...
[INFO] Simulation engine initialized
[INFO] Mission generator active
```

### Step 6: Deactivate the Virtual Environment (When Done)

```bash
deactivate
```

---

## Complete Project Structure

```
MJN/
├── drone-command-center/          ← Frontend (Next.js + TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           ← Main dashboard
│   │   │   ├── layout.tsx         ← Root layout
│   │   │   └── globals.css        ← Global styles (charcoal theme)
│   │   ├── components/
│   │   │   ├── gcs/               ← Dashboard components
│   │   │   │   ├── AlertPanel.tsx     ← Floating critical alerts
│   │   │   │   ├── AIPanel.tsx        ← Brain engine status
│   │   │   │   ├── AttitudeIndicator.tsx ← Artificial horizon
│   │   │   │   ├── Compass.tsx        ← Compass rose
│   │   │   │   ├── EventConsole.tsx   ← Event log
│   │   │   │   └── ... (more panels)
│   │   │   └── gis/               ← GIS / Map components
│   │   │       ├── GISMap.tsx         ← Map container
│   │   │       ├── MapEngine.ts       ← Map lifecycle
│   │   │       ├── MapFollowController.ts ← Camera behavior
│   │   │       ├── PathManager.ts     ← Route polylines
│   │   │       ├── WaypointRenderer.ts ← Waypoint markers
│   │   │       ├── LiveDroneMarker.ts ← Drone icon
│   │   │       └── ... (more)
│   │   ├── store/                 ← Zustand state stores
│   │   │   ├── droneEntityStore.ts   ← Single source of truth
│   │   │   ├── simulationEngine.ts   ← 20Hz drone simulation
│   │   │   ├── missionGenerator.ts   ← Mission/waypoint gen
│   │   │   ├── eventEngine.ts        ← Event detection
│   │   │   └── mapStore.ts           ← Map settings
│   │   ├── hooks/                 ← Custom React hooks
│   │   │   └── useEventEngine.ts
│   │   └── types/                 ← TypeScript interfaces
│   │       └── droneEntity.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── README.md                  ← Architecture documentation
│   └── SETUP.md                   ← This file
├── src/                           ← Python backend
│   ├── core/                      ← Physics, mission, event bus
│   ├── airspace/                  ← Geofence, no-fly zones
│   ├── autonomy/                  ← Navigation, planning
│   └── ...
├── requirements.txt               ← Python dependencies
├── main.py                        ← Python entry point
└── .gitignore
```

---

## Common Errors & Solutions

### Error: `npm install` fails

```
npm ERR! code ENOENT
npm ERR! syscall open
```

**Solution:** Make sure you're in the `drone-command-center` directory:

```bash
cd MJN/drone-command-center
npm install
```

### Error: `'npm' is not recognized`

**Solution:** Node.js is not installed or not in PATH.

1. Download and install from https://nodejs.org/
2. Restart your terminal
3. Verify: `node --version` and `npm --version`

### Error: Port 3000 already in use

```
Error: listen EADDRINUSE :::3000
```

**Solution:** Either kill the process using port 3000, or use a different port:

```bash
# Kill process on port 3000 (Windows)
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Kill process on port 3000 (macOS/Linux)
lsof -i :3000
kill -9 <PID>

# Or use a different port
npm run dev -- -p 3001
```

### Error: `Module not found: Can't resolve ...`

**Solution:** Delete `node_modules` and reinstall:

```bash
# Windows
rmdir /S node_modules
del package-lock.json
npm install

# macOS/Linux
rm -rf node_modules package-lock.json
npm install
```

### Error: `venv\Scripts\activate` does not exist

**Solution:** You haven't created the virtual environment yet:

```bash
python -m venv venv
# Then activate:
venv\Scripts\activate
```

### Error: `python` not found (Windows)

**Solution 1:** Install Python from python.org (check "Add to PATH").
**Solution 2:** Use the full path:

```bash
C:\Python311\python.exe -m venv venv
```

Or use `py` launcher:

```bash
py -m venv venv
```

### Error: PowerShell execution policy blocks script

```
venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Solution:**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

Or use Command Prompt instead of PowerShell:

```cmd
venv\Scripts\activate.bat
```

### Error: `pip install -r requirements.txt` fails

**Solution:** Upgrade pip first:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Error: Map tiles not loading in the dashboard

```
Tile load failed
```

**Solution:** Check your internet connection. The dashboard falls back to a tactical grid pattern automatically when tiles fail.

### Error: Dashboard shows blank page

**Solution:** Check the browser console for errors (F12 → Console tab). Common issues:

1. **Refresh the page** (F5) — sometimes fixes hydration issues
2. **Clear browser cache**: Ctrl+Shift+Delete → Cached images and files
3. **Check the terminal** running `npm run dev` for compilation errors

---

## Quick Start Commands (Copy & Paste)

### Frontend Only (No Backend Required)

#### Windows (Command Prompt)

```cmd
# 1. Clone
git clone https://github.com/sherly7Veronica/MJN.git
cd MJN\drone-command-center

# 2. Install
npm install

# 3. Run
npm run dev
```

#### Windows (PowerShell)

```powershell
# 1. Clone
git clone https://github.com/sherly7Veronica/MJN.git
Set-Location MJN\drone-command-center

# 2. Install
npm install

# 3. Run
npm run dev
```

#### macOS / Linux

```bash
# 1. Clone
git clone https://github.com/sherly7Veronica/MJN.git
cd MJN/drone-command-center

# 2. Install
npm install

# 3. Run
npm run dev
```

### Frontend + Python Backend (Full Setup)

#### Windows (Command Prompt)

```cmd
:: Terminal 1: Python Backend
cd MJN
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py

:: Terminal 2: Frontend (open a new terminal)
cd MJN\drone-command-center
npm install
npm run dev
```

#### Windows (PowerShell)

```powershell
# Terminal 1: Python Backend
Set-Location MJN
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py

# Terminal 2: Frontend (open a new terminal)
Set-Location MJN\drone-command-center
npm install
npm run dev
```

#### macOS / Linux

```bash
# Terminal 1: Python Backend
cd MJN
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Terminal 2: Frontend (open a new terminal)
cd MJN/drone-command-center
npm install
npm run dev
```

---

## Verification Checklist

After setup, verify everything works:

- [ ] `npm run dev` starts without errors
- [ ] http://localhost:3000 loads the dashboard
- [ ] Map shows OpenStreetMap tiles (street view)
- [ ] Drone marker moves along a route
- [ ] Waypoints are visible (home, destination, numbered)
- [ ] Left panel shows live telemetry values
- [ ] Right panel shows mission progress
- [ ] Bottom bar shows instruments (attitude, compass, ALT, SPD)
- [ ] Heading matches between drone marker and IMU
- [ ] Battery percentage changes over time
- [ ] Events appear when clicking "Events" button
- [ ] Alerts show up for low battery/wind/obstacles

---

## Need Help?

- **GitHub Issues:** https://github.com/sherly7Veronica/MJN/issues
- **Dashboard running:** http://localhost:3000
- **Build verification:** `npm run build` (must pass without errors)