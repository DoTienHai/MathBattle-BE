# �️ PostgreSQL 18 Setup & Troubleshooting

## 📋 Quick Start

### 1. Start PostgreSQL Service

Open **PowerShell as Administrator**:

```powershell
# Start service
Start-Service postgresql-x64-18

# or using net command
net start postgresql-x64-18
```

### 2. Check Service Status

```powershell
Get-Service postgresql-x64-18
# Result should be: Running
```

### 3. Test Database Connection

```powershell
psql -U postgres
# Should see prompt: postgres=#
```

### 4. Create mathbattle Database

```sql
CREATE DATABASE mathbattle;
\q
```

---

## ⚙️ Auto Start on Boot

### PowerShell Method (Recommended)

```powershell
# Set PostgreSQL to auto-start on boot
Set-Service -Name postgresql-x64-18 -StartupType Automatic

# Verify
Get-Service postgresql-x64-18 | Select-Object Name, StartType
# Result: StartType = Automatic
```

### Services GUI Method

1. Win + R → `services.msc` → Enter
2. Find **postgresql-x64-18**
3. Right-click → **Properties**
4. **Startup type**: Select **Automatic**
5. Click **OK**

---

## 🔍 Useful Commands

### Check Service Details

```powershell
# View all PostgreSQL services
Get-Service | Where-Object {$_.Name -like "*postgres*"}

# Check specific service
Get-Service postgresql-x64-18 | Select-Object Name, Status, StartType

# Check service startup type values
# 2 = Automatic, 3 = Manual, 4 = Disabled
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\postgresql-x64-18" -Name Start
```

### Stop PostgreSQL

```powershell
Stop-Service postgresql-x64-18
# or
net stop postgresql-x64-18
```

### Restart PostgreSQL

```powershell
Restart-Service postgresql-x64-18
```

---

## 🐛 Troubleshooting

### Connection Timeout / Connection Refused

**Problem**: 
```
connection timeout expired
Connect call failed ('::1', 5432) or ('127.0.0.1', 5432)
```

**Solution**:
```powershell
# 1. Check if service is running
Get-Service postgresql-x64-18

# 2. Start if Stopped
Start-Service postgresql-x64-18

# 3. Wait 2-3 seconds and test
psql -U postgres
```

### Wrong psql Version (Using 25 instead of 18)

**Problem**: `psql --version` shows PostgreSQL 25 but you need 18

**Solution**:
1. Win + R → `sysdm.cpl` → Enter
2. **Environment Variables**
3. Find `Path` variable
4. Move `C:\Program Files\PostgreSQL\18\bin` to the **top**
5. Close and reopen terminal
6. Test: `psql --version`

### Port 5432 Already in Use

**Problem**: Service won't start because port is taken

**Solution**:
```powershell
# Find what's using port 5432
netstat -ano | findstr :5432

# Kill the process (replace <PID> with actual number)
taskkill /PID <PID> /F

# Or check if multiple PostgreSQL versions running
Get-Service | Where-Object {$_.Name -like "*postgres*"} | Select-Object Name, Status
```

### Database "mathbattle" Not Found

**Solution**:
```powershell
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE mathbattle;

# List databases
\l

# Exit
\q
```

### Forgot PostgreSQL Password

**Solution**:
```powershell
# Reset password for postgres user
psql -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD 'new_password';"
```

### PostgreSQL Won't Start

**Problem**: Service stuck or won't start

**Solution**:
```powershell
# 1. Check service log
Get-EventLog -LogName Application -Source PostgreSQL | Select-Object -First 20

# 2. Try manual start to see error
pg_ctl -D "C:\Program Files\PostgreSQL\18\data" start

# 3. If data corruption, reinstall PostgreSQL
# Backup first: C:\Program Files\PostgreSQL\18\data
```

---

## 📝 Connection String for MathBattle-BE

Add to `.env` file:

```env
# Default (no password)
DATABASE_URL=postgresql+asyncpg://postgres@localhost/mathbattle

# With password
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/mathbattle

# With custom port
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mathbattle
```

---

## 🔐 Security Notes

- Default username: `postgres`
- Default port: `5432`
- Password: Set during PostgreSQL installation
- For production: Use strong password & external authentication

---

## 📋 Startup Type Reference

| Type | Value | Auto-Start | Manual-Start |
|---|---|---|---|
| Automatic | 2 | ✅ Yes | ✅ Yes |
| Manual | 3 | ❌ No | ✅ Yes |
| Disabled | 4 | ❌ No | ❌ No |

---

**Last Updated**: May 7, 2026
