# Unity Configuration Backup - Quick Start Guide

## 🚀 Python Script for Unity Configuration Backups

This guide covers the **Python script** for creating and downloading Unity configuration backups from your Dell Unisphere system.

### 📁 Essential Files:
- `create_unity_backup.py` - Main Python script with Selenium WebDriver automation
- `requirements.txt` - Python package dependencies
- `Run-UnityBackups.ps1` - PowerShell automation script for multiple Unity systems
- `unity_ips.txt` - List of Unity IP addresses for batch processing

### 📁 Archived Files (in E:\Unity-Old):
- PowerShell wrapper scripts (Create-UnityBackup.ps1, Execute-UnityBackup.ps1)
- Development files and older versions

## 🐍 Python Script Usage

### Prerequisites:
```bash
pip install -r requirements.txt
```

### Basic Usage:
```bash
# Using Chrome browser (recommended for Unity)
python create_unity_backup.py UNITY-IP your-username@domain.com your-password

# Using Edge browser
python create_unity_backup.py --browser edge UNITY-IP your-username@domain.com your-password
```

### Command Line Arguments:
- `unity_url` - Unity Unisphere URL (e.g., UNITY-IP)
- `username` - Username for Unity Unisphere
- `password` - Password for Unity Unisphere
- `--browser {chrome,edge}` - Browser to use (default: chrome)

### Example with your Unity system:
```bash
python create_unity_backup.py UNITY-IP USERNAME your-password --browser chrome
```

## 🔄 PowerShell Automation Script (Recommended)

### For Multiple Unity Systems:
The PowerShell script `Run-UnityBackups.ps1` automates backups for multiple Unity systems:

```powershell
# Interactive mode - prompts for credentials and processes all IPs in unity_ips.txt
.\Run-UnityBackups.ps1

# Specify custom IP list file and browser
.\Run-UnityBackups.ps1 -IPListFile "my_unity_systems.txt" -Browser edge
```

### Features:
- **📋 Batch Processing** - Processes multiple Unity systems from IP list file
- **🔐 Secure Credential Prompt** - Prompts for username/password interactively
- **📝 Detailed Logging** - Creates timestamped log files for tracking
- **✅ Error Handling** - Continues processing even if one system fails
- **⏸️ Rate Limiting** - Waits between systems to avoid network overload
- **📊 Summary Report** - Shows success/failure counts and duration

### IP List File Format:
Edit `unity_ips.txt` to include your Unity systems:
```text
# Unity IP Address List
# One IP address per line
10.213.182.85
192.168.1.100
172.16.0.50
```

## 🎯 How It Works

The Python script performs the following automation sequence:

### Stage 1: Configuration Backup
1. **🌐 Connect** to Unity Unisphere web interface
2. **🔐 Login** with provided credentials  
3. **📂 Navigate** to Service Tasks → Save Configuration
4. **🚀 Execute** the backup creation process
5. **💬 Handle** dialog boxes (select "Create New" backup)
6. **⏳ Wait** for backup job completion
7. **⬇️ Download** the generated backup file
8. **📁 Save** to `E:\Unity\Configuration backups\` with naming: `unity_backup_YYYY-MM-DD_HHMMSS-IP-{ip}.{ext}`

### Stage 2: Encryption Keystore Backup
1. **⚙️ Navigate** to Settings → Management → Encryption
2. **🔑 Click** "Backup Keystore File"
3. **⬇️ Download** the keystore backup (.lbb file)
4. **📁 Save** to `E:\Unity\Encryption Key Backups\` with naming: `Unity-Encryption-Backup_YYYY-MM-DD_HHMMSS-IP-{ip}.lbb`

## 📊 Features

### ✅ Browser Support:
- **Chrome** - Recommended for Unity, enhanced optimizations
- **Edge** - Alternative browser option

### ✅ Automation Features:
- Automatic certificate warning bypass
- Security disclaimer handling
- Login form detection and completion
- Dialog box interaction
- Download management
- Error recovery

### ✅ Output Management:
- Organized directory structure
- Detailed logging
- Progress indicators
- Error reporting

## 📁 Directory Structure:
```
E:\Unity\
├── create_unity_backup.py         # Main Python script
├── requirements.txt               # Python dependencies
├── Run-UnityBackups.ps1           # PowerShell automation script
├── unity_ips.txt                  # Unity IP addresses list
├── BACKUP_CREATION_GUIDE.md      # This guide
├── Configuration backups/         # Downloaded configuration backup files
│   └── unity_backup_YYYY-MM-DD_HHMMSS-IP-{ip}.html
├── Encryption Key Backups/       # Downloaded keystore backup files
│   └── Unity-Encryption-Backup_YYYY-MM-DD_HHMMSS-IP-{ip}.lbb
└── unity_backups/debug/          # Debug files (screenshots, HTML dumps)

E:\Unity-Old/                     # Archived files
├── .vscode/                      # VS Code configuration
├── Create-UnityBackup.ps1        # PowerShell wrapper script
├── Execute-UnityBackup.ps1       # PowerShell execution script
├── PRODUCTION_USAGE_GUIDE.md     # Additional documentation
└── [other development files...]
```

## 🔧 Command Line Options

### Available Arguments:
- `unity_url` - Unity Unisphere URL (required)
- `username` - Username for Unity Unisphere (required) 
- `password` - Password for Unity Unisphere (required)
- `--browser {chrome,edge}` - Browser selection (optional, default: chrome)

### Help:
```bash
python create_unity_backup.py --help
```

## 🚨 Troubleshooting

### Common Issues:
1. **Certificate Errors** - Scripts handle these automatically
2. **Login Failures** - Verify credentials and URL
3. **Download Issues** - Check firewall/antivirus settings
4. **Browser Issues** - Try different browser option

### Debug Mode:
```bash
# Run with detailed logging
python create_unity_backup.py UNITY-IP your-username your-password --browser chrome
```

## 📋 Log Files

The script creates detailed log files:
- `unity_backup_YYYYMMDD_HHMMSS.log` - Main execution log with detailed automation steps

## 🎯 Quick Test

To test with your Unity system:

```bash
python create_unity_backup.py UNITY-IP USERNAME your-password
```

The script will:
- ✅ Connect to your Unity system
- ✅ Login automatically  
- ✅ Create a new configuration backup
- ✅ Download the configuration backup file
- ✅ Save it to `E:\Unity\Configuration backups\`
- ✅ Navigate to Settings → Management → Encryption
- ✅ Create and download encryption keystore backup
- ✅ Save it to `E:\Unity\Encryption Key Backups\`

## 📦 Installation

### For Single System Backup:
1. **Clone or download** the files to `E:\Unity\`
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run the script**: `python create_unity_backup.py <unity_url> <username> <password>`

### For Multiple Systems (Recommended):
1. **Clone or download** the files to `E:\Unity\`
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Edit IP list**: Add your Unity IP addresses to `unity_ips.txt`
4. **Run automation**: `.\Run-UnityBackups.ps1`

## 🔗 Additional Resources

- PowerShell wrapper scripts are available in `E:\Unity-Old\` for convenience
- Additional documentation and development files are archived in `E:\Unity-Old\`

Ready to backup your Unity configuration! 🚀
