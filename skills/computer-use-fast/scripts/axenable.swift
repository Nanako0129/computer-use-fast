// cu-axenable <pid> — ask a Chromium or Electron app to expose its web content to accessibility clients.
// Chrome and Electron build their AX tree only when an assistive client asks (AXManualAccessibility); until
// then cua-driver sees the menu bar and nothing else. Setting the attribute needs this binary to be trusted
// for Accessibility, which only the person can grant (System Settings → Privacy & Security → Accessibility).
// Chrome 154 answers both writes below with an error (-25205 / -25208) yet turns its accessibility on anyway
// (chrome://accessibility then lists VoiceOver as the active assistive technology), so cu.py judges success by
// whether a web area appears, not by this exit code. Electron apps accept AXManualAccessibility outright.
// Build: swiftc -O axenable.swift -o ~/.local/share/computer-use-fast/cu-axenable
import ApplicationServices
import Foundation

let args = CommandLine.arguments
guard args.count == 2, let pid = pid_t(args[1]) else {
    FileHandle.standardError.write("usage: cu-axenable <pid>\n".data(using: .utf8)!)
    exit(2)
}
let prompt = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
guard AXIsProcessTrustedWithOptions([prompt: true] as CFDictionary) else {
    print("not trusted: allow \(args[0]) in System Settings > Privacy & Security > Accessibility")
    exit(3)
}
let app = AXUIElementCreateApplication(pid)
let manual = AXUIElementSetAttributeValue(app, "AXManualAccessibility" as CFString, kCFBooleanTrue)
if manual != .success {
    // Older Chromium answers only to the VoiceOver-style switch.
    let enhanced = AXUIElementSetAttributeValue(app, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
    print(enhanced == .success ? "ok (AXEnhancedUserInterface)" : "failed: \(manual.rawValue) / \(enhanced.rawValue)")
    exit(enhanced == .success ? 0 : 1)
}
print("ok")
