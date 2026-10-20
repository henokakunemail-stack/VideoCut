; ============================================================
;  VideoCut — NSIS Installer Script
;  Requires: NSIS 3.x  (https://nsis.sourceforge.io)
;  Run after PyInstaller: makensis installer\setup.nsi
; ============================================================

!define APP_NAME        "VideoCut"
!define APP_VERSION     "2.0.0"
!define APP_PUBLISHER   "Henok"
!define APP_EXE         "VideoCut.exe"
!define APP_DIR_NAME    "VideoCut"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_DIR_NAME}"
!define REG_KEY         "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define ICON_FILE       "..\assets\icons\app.ico"

; ---- Metadata ------------------------------------------------
Name            "${APP_NAME} ${APP_VERSION}"
OutFile         "VideoCut_Setup.exe"
InstallDir      "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor   /SOLID lzma
Unicode         True

; ---- Modern UI -----------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON            "${ICON_FILE}"
!define MUI_UNICON          "${ICON_FILE}"
; !define MUI_WELCOMEFINISHPAGE_BITMAP   ; skip, use default
; !define MUI_HEADERIMAGE
; !define MUI_HEADERIMAGE_RIGHT

; Welcome page
!define MUI_WELCOMEPAGE_TITLE   "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT    "This wizard will guide you through the installation of ${APP_NAME} ${APP_VERSION}.$\r$\n$\r$\nA powerful video editor with filters, effects, and timeline editing.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

; License page (optional — remove if not needed)
; !insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"

; Directory page
!insertmacro MUI_PAGE_DIRECTORY

; Components page
!insertmacro MUI_PAGE_COMPONENTS

; Install files page
!insertmacro MUI_PAGE_INSTFILES

; Finish page
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_SHOWREADME   "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "View README"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ---- Components ----------------------------------------------
Section "Main Application" SecMain
    SectionIn RO      ; Required — cannot uncheck
    SetOutPath "$INSTDIR"

    ; Copy all files from PyInstaller dist folder
    File /r "..\dist\VideoCut\*.*"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry entries for Add/Remove Programs
    WriteRegStr   HKLM "${REG_KEY}" "DisplayName"     "${APP_NAME}"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"  "${APP_VERSION}"
    WriteRegStr   HKLM "${REG_KEY}" "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr   HKLM "${REG_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
    WriteRegDWORD HKLM "${REG_KEY}" "NoModify"        1
    WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"        1

    ; Estimate installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize" "$0"
SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" \
        "$INSTDIR\${APP_EXE}" 0 \
        SW_SHOWNORMAL "" "${APP_NAME}"
SectionEnd

Section "Start Menu Shortcut" SecStartMenu
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\${APP_EXE}" "" \
        "$INSTDIR\${APP_EXE}" 0
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
        "$INSTDIR\Uninstall.exe"
SectionEnd

; Section descriptions shown on Components page
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}      "Core application files (required)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop}   "Add a shortcut on the Desktop"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} "Add shortcuts in the Start Menu"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ---- Uninstaller ---------------------------------------------
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"

    ; Remove registry
    DeleteRegKey HKLM "${REG_KEY}"
SectionEnd
