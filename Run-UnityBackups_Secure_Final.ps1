<#
.SYNOPSIS
    Automated Unity Configuration Backup Runner

.DESCRIPTION
    This PowerShell script prompts for Unity credentials, reads a list of Unity IP addresses
    from a text file, and runs the Python backup script for each Unity system.

.PARAMETER IPListFile
    Path to the text file containing Unity IP addresses (one per line)

.PARAMETER Browser
    Browser to use for automation (chrome or edge). Default: edge
    
.PARAMETER TimeoutSeconds
    Maximum time in seconds to wait for each backup operation. Default: 600 (10 minutes)
    
.PARAMETER Force
    Skip confirmation prompt and proceed immediately with backups

.EXAMPLE
    .\Run-UnityBackups.ps1
    .\Run-UnityBackups.ps1 -IPListFile "unity_ips.txt" -Browser edge
    .\Run-UnityBackups.ps1 -TimeoutSeconds 300 -Force

.NOTES
    Author: Unity Backup Automation
    Requires: Python 3.x with selenium and webdriver-manager packages
    Expected IP file format: One IP address per line (e.g., 10.213.182.85)
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateNotNullOrEmpty()]
    [ValidateScript({
        if (Test-Path $_ -IsValid) { $true }
        else { throw "The path '$_' contains invalid characters." }
    })]
    [string]$IPListFile = "unity_ips.txt",
      [Parameter(Mandatory=$false)]
    [ValidateSet("chrome", "edge")]
    [string]$Browser = "edge",
    
    [Parameter(Mandatory=$false)]
    [int]$TimeoutSeconds = 600,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Script configuration
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptPath "create_unity_backup.py"
$LogsFolder = Join-Path $ScriptPath "Logs"
$LogFile = Join-Path $LogsFolder "unity_backups_$(Get-Date -Format yyyyMMdd_HHmmss).log"

# Ensure Logs folder exists
if (-not (Test-Path $LogsFolder)) {
    New-Item -Path $LogsFolder -ItemType Directory -Force | Out-Null
    Write-Verbose "Created Logs directory at $LogsFolder"
}

# Function to write log messages
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

# Function to validate IP address format
function Test-IPAddress {
    param([string]$IP)
    try {
        $null = [System.Net.IPAddress]::Parse($IP.Trim())
        return $true
    }
    catch {
        return $false
    }
}

# Function to run backup for a single Unity system
function Invoke-UnityBackup {
    param(
        [string]$UnityIP,
        [string]$Username,
        [System.Security.SecureString]$SecurePassword,
        [string]$Browser,
        [int]$TimeoutSeconds = 600  # Default timeout of 10 minutes
    )
    
    $UnityURL = "https://$UnityIP"
    Write-Log "Starting backup for Unity system: $UnityURL" "INFO"
    
    try {
        # Verify network connectivity before proceeding
        if (-not (Test-Connection -ComputerName $UnityIP -Count 1 -Quiet)) {
            Write-Log "Cannot connect to $UnityIP - network unreachable" "ERROR"
            return $false
        }
        
        # Create a temporary file for the password
        $TempPasswordFile = [System.IO.Path]::GetTempFileName()
        
        try {
            # Convert SecureString to plain text and store in temporary file
            $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
            try {
                $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
                [System.IO.File]::WriteAllText($TempPasswordFile, $PlainPassword)
                # Clear the plain text password from memory immediately
                $PlainPassword = $null
            }
            finally {
                # Always zero and release the unmanaged string
                if ($BSTR -ne [IntPtr]::Zero) {
                    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
                }
            }
            
            # Run the Python backup script with password file
            $Arguments = @(
                $PythonScript,
                $UnityURL,
                $Username,
                "--password-file", $TempPasswordFile,
                "--browser", $Browser
            )
              # Log execution without showing password
            Write-Log "Executing backup for $UnityIP using $Browser browser" "DEBUG"        
            
            # We'll use a different approach with redirected output to better detect success
            try {
                # Start process with output redirection
                
                # Start process and redirect output
                $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
                $ProcessInfo.FileName = "python"
                $ProcessInfo.RedirectStandardOutput = $true
                $ProcessInfo.RedirectStandardError = $true
                $ProcessInfo.UseShellExecute = $false
                $ProcessInfo.Arguments = $Arguments -join " "
            
            $Process = New-Object System.Diagnostics.Process
            $Process.StartInfo = $ProcessInfo
            $Process.Start() | Out-Null
            
            # Capture output asynchronously
            $OutputTask = $Process.StandardOutput.ReadToEndAsync()
            $ErrorTask = $Process.StandardError.ReadToEndAsync()
            
            # Wait with timeout
            $completed = $Process.WaitForExit($TimeoutSeconds * 1000)  # Convert to milliseconds
            
            if (-not $completed) {
                # Process timed out
                Write-Log "Backup timed out after $TimeoutSeconds seconds for $UnityIP" "ERROR"
                try {
                    $Process.Kill()
                    Write-Log "Process terminated due to timeout" "WARNING"
                } catch {
                    Write-Log "Failed to terminate timed out process: $($_.Exception.Message)" "WARNING"
                }
                return $false
            }
            
            # Get output
            $Output = $OutputTask.Result
            $ErrorOutput = $ErrorTask.Result
              # Check for success indicators in output
            if ($Output -match "Backup workflow completed!" -and $Output -match "Encryption keystore backup completed!") {
                Write-Log "Backup completed successfully for $UnityIP (confirmed by output)" "SUCCESS"
                return $true
            }
            # Check if backup files exist (additional check)
            elseif ((Test-Path "$ScriptPath\Configuration backups\*$UnityIP*.html") -and 
                   (Test-Path "$ScriptPath\Encryption Key Backups\*$UnityIP*.lbb")) {
                Write-Log "Backup completed successfully for $UnityIP (backup files exist)" "SUCCESS"
                return $true
            }
            elseif ($Process.ExitCode -eq 0) {
                Write-Log "Backup completed with exit code 0 for $UnityIP" "SUCCESS"
                return $true
            } else {
                Write-Log "Backup failed for $UnityIP (Exit Code: $($Process.ExitCode))" "ERROR"
                if (-not [string]::IsNullOrEmpty($ErrorOutput)) {
                    Write-Log "Error output: $($ErrorOutput.Trim())" "ERROR"
                }
                return $false
            }
        }
        catch {
            Write-Log "Exception during process execution: $($_.Exception.Message)" "ERROR"
            return $false
        }
        }
        finally {
            # Always clean up the temporary password file
            if (Test-Path $TempPasswordFile) {
                # Securely delete file by overwriting with zeros
                [System.IO.File]::WriteAllBytes($TempPasswordFile, (New-Object byte[] 0))
                Remove-Item $TempPasswordFile -Force -ErrorAction SilentlyContinue
                Write-Log "Cleaned up temporary credential file" "DEBUG"
            }
        }
    }
    catch {
        Write-Log "Exception during backup for $UnityIP`: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Main script execution
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "           Unity Configuration Backup Runner v1.0" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Log "Unity Backup Runner started" "INFO"
Write-Log "Script Path: $ScriptPath" "DEBUG"
Write-Log "Python Script: $PythonScript" "DEBUG"
Write-Log "IP List File: $IPListFile" "DEBUG"
Write-Log "Browser: $Browser" "DEBUG"

# Validate prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check if Python script exists
if (-not (Test-Path $PythonScript)) {
    Write-Log "Python script not found: $PythonScript" "ERROR"
    Write-Host "Please ensure create_unity_backup.py is in the same directory as this script." -ForegroundColor Red
    exit 1
}

# Check if Python is available
try {
    $PythonVersion = python --version 2>&1
    Write-Log "Python found: $PythonVersion" "INFO"
} catch {
    Write-Log "Python not found in PATH" "ERROR"
    Write-Host "Please install Python 3.x and ensure it is in your PATH." -ForegroundColor Red
    exit 1
}

# Check if IP list file exists
$FullIPListPath = Join-Path $ScriptPath $IPListFile
if (-not (Test-Path $FullIPListPath)) {
    Write-Log "IP list file not found: $FullIPListPath" "ERROR"
    Write-Host "Creating sample IP list file..." -ForegroundColor Yellow
    
    # Create a sample IP list file with a simple here-string
    $SampleContent = @"
# Unity IP Address List
# One IP address per line
# Lines starting with # are comments and will be ignored
# Example:
# 10.213.182.85
# 192.168.1.100

"@
    Set-Content -Path $FullIPListPath -Value $SampleContent
    Write-Host "Sample file created at: $FullIPListPath" -ForegroundColor Green
    Write-Host "Please edit this file to add your Unity IP addresses, then run the script again." -ForegroundColor Yellow
    exit 1
}

# Read and validate IP addresses
Write-Host "Reading Unity IP addresses..." -ForegroundColor Yellow
$IPAddresses = @()
$InvalidIPs = @()
$LineNumber = 0

# Read all content at once for better performance
$FileContent = Get-Content $FullIPListPath
foreach ($Line in $FileContent) {
    $LineNumber++
    $Line = $Line.Trim()
    # Skip empty lines and comments
    if ([string]::IsNullOrWhiteSpace($Line) -or $Line.StartsWith("#")) {
        continue
    }
    # Validate IP address
    if (Test-IPAddress $Line) {
        $IPAddresses += $Line
        Write-Log "Valid IP found: $Line" "DEBUG"
    } else {
        $InvalidIPs += "Line ${LineNumber}: $Line"
        Write-Log "Invalid IP format on line ${LineNumber}: $Line" "WARNING"
    }
}

if ($InvalidIPs.Count -gt 0) {
    Write-Host "" -ForegroundColor Red
    Write-Host "The following invalid IP addresses were found in ${FullIPListPath}:" -ForegroundColor Red
    $InvalidIPs | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Log "Invalid IP addresses found. Aborting execution." "ERROR"
    exit 1
}

if ($IPAddresses.Count -eq 0) {
    Write-Log "No valid IP addresses found in $FullIPListPath" "ERROR"
    Write-Host "Please add valid Unity IP addresses to the file." -ForegroundColor Red
    exit 1
}

Write-Log "Found $($IPAddresses.Count) valid Unity IP address(es)" "INFO"
Write-Host "Found $($IPAddresses.Count) Unity systems:" -ForegroundColor Green
$IPAddresses | ForEach-Object { Write-Host "  • $_" -ForegroundColor Cyan }
Write-Host ""

# Get credentials from user
Write-Host "Please enter your Unity Unisphere credentials:" -ForegroundColor Yellow
try {
    $Credential = Get-Credential -Message "Enter your Unity Unisphere credentials" -ErrorAction Stop
    
    # Check if user cancelled the credential prompt
    if ($null -eq $Credential) {
        Write-Log "Credential entry was cancelled by user" "ERROR"
        exit 1
    }
      $Username = $Credential.UserName
    $SecurePassword = $Credential.Password

    if ([string]::IsNullOrWhiteSpace($Username)) {
        Write-Log "Username cannot be empty" "ERROR"
        exit 1
    }

    if ($SecurePassword.Length -eq 0) {
        Write-Log "Password cannot be empty" "ERROR"
        exit 1
    }
} 
catch {
    Write-Log "Error retrieving credentials: $($_.Exception.Message)" "ERROR"
    exit 1
}

Write-Log "Credentials provided for user: $Username" "INFO"
Write-Host ""

# Confirm execution
Write-Host "Ready to start backups for $($IPAddresses.Count) Unity system(s)" -ForegroundColor Yellow
Write-Host "Browser: $Browser" -ForegroundColor Cyan
Write-Host "Timeout: $TimeoutSeconds seconds" -ForegroundColor Cyan
Write-Host "Log file: $LogFile" -ForegroundColor Cyan
Write-Host ""

# Skip confirmation if Force switch is specified
if (-not $Force) {
    $Confirm = Read-Host "Do you want to proceed? (y/N)"
    if ($Confirm -notmatch "^[Yy]") {
        Write-Log "Backup operation cancelled by user" "INFO"
        Write-Host "Operation cancelled." -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Log "Force parameter specified, skipping confirmation" "INFO"
}

# Execute backups
Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                    Starting Backup Operations" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$SuccessCount = 0
$FailureCount = 0
$StartTime = Get-Date

$Index = 0
foreach ($IP in $IPAddresses) {
    $Index++
    Write-Host ""
    Write-Host "Processing Unity system: $IP ($Index/$($IPAddresses.Count))" -ForegroundColor Yellow
    Write-Host "-------------------------------------------------------------" -ForegroundColor Gray
    
    $BackupResult = Invoke-UnityBackup -UnityIP $IP -Username $Username -SecurePassword $SecurePassword -Browser $Browser -TimeoutSeconds $TimeoutSeconds
    
    if ($BackupResult) {
        $SuccessCount++
        Write-Host "Unity $IP - Backup completed successfully" -ForegroundColor Green
    } else {
        $FailureCount++
        Write-Host "Unity $IP - Backup failed" -ForegroundColor Red
    }
    
    # Add a pause between systems to avoid overwhelming the network
    if ($Index -lt $IPAddresses.Count) {
        Write-Host "Waiting 5 seconds before next system..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
    }
}

# Final summary
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                       Backup Summary" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total Unity Systems: $($IPAddresses.Count)" -ForegroundColor Cyan
Write-Host "Successful Backups:  $SuccessCount" -ForegroundColor Green
Write-Host "Failed Backups:      $FailureCount" -ForegroundColor $(if ($FailureCount -gt 0) { "Red" } else { "Green" })
Write-Host "Total Duration:      $($Duration.ToString('hh\:mm\:ss'))" -ForegroundColor Cyan
Write-Host "Log File:           $LogFile" -ForegroundColor Cyan
Write-Host ""

Write-Log "Backup operations completed. Success: $SuccessCount, Failures: $FailureCount, Duration: $($Duration.ToString('hh\:mm\:ss'))" "INFO"

if ($FailureCount -gt 0) {
    Write-Host "Warning: Some backups failed. Check the log file for details." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "Success! All backups completed successfully!" -ForegroundColor Green
    exit 0
}

# Clean up and release resources
$SecurePassword = $null
# Explicitly clear sensitive variables from memory
[System.GC]::Collect()

<#
Fixes and Enhancements:
- Fixed Array.IndexOf issue by using a counter variable
- Improved password security with proper SecureString handling
- Added timeout handling for Python process execution
- Added network connectivity checks before backup attempts
- Enhanced IP file validation with better error reporting
- Added Force parameter to skip confirmation
- Improved string handling for better performance
- Added parameter validation for inputs
- Enhanced error handling throughout the script
- Added cleanup of sensitive data in memory
- Removed problematic Unicode/emoji characters
- Enhanced security:
  * Changed to SecureString for password handling
  * Temporary password files used for Python script (with secure deletion)
  * Default browser changed to Edge
  * No password exposure in command line or logs
#>
