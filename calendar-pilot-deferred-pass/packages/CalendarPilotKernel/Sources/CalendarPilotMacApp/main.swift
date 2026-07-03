
import Foundation

#if canImport(AppKit) && canImport(WebKit)
import AppKit
import WebKit

struct CalendarPilotLaunchConfig: Codable {
    let status: String
    let launchID: String
    let buildID: String
    let appBundlePath: String
    let appRoot: String
    let runDir: String
    let staticDir: String
    let pythonExecutable: String
    let host: String
    let port: Int
    let runtimeMode: String
    let kernelServerPath: String
    let eventKitBridgePath: String
    let startedAt: String
    let launcherPID: Int32
    let serverPID: Int32?
    let updatedAt: String

    var baseURL: URL {
        URL(string: "http://\(host):\(port)")!
    }

    static func fromEnvironment() -> CalendarPilotLaunchConfig {
        let env = ProcessInfo.processInfo.environment
        let bundleURL = Bundle.main.bundleURL
        let resources = Bundle.main.resourceURL ?? bundleURL.appendingPathComponent("Contents/Resources")
        let appRoot = env["CALENDAR_PILOT_APP_ROOT"].flatMap(URL.init(fileURLWithPath:))
            ?? resources.appendingPathComponent("app", isDirectory: true)
        let defaultRunDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/CalendarPilot", isDirectory: true)
        let runDir = env["CALENDAR_PILOT_RUN_DIR"].flatMap(URL.init(fileURLWithPath:)) ?? defaultRunDir
        let binDir = appRoot.appendingPathComponent("bin", isDirectory: true)
        let kernelPath = env["CALENDAR_PILOT_SWIFT_KERNEL_SERVER"]
            ?? binDir.appendingPathComponent("CalendarPilotKernelServer").path
        let bridgePath = env["CALENDAR_PILOT_EVENTKIT_BRIDGE"]
            ?? binDir.appendingPathComponent("CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge").path
        let buildIDPath = appRoot.appendingPathComponent("build_id")
        let buildID = env["CALENDAR_PILOT_BUILD_ID"]
            ?? ((try? String(contentsOf: buildIDPath, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines))
            ?? "unknown"
        let requestedPort = Int(env["CALENDAR_PILOT_PORT"] ?? "8787") ?? 8787
        let selectedPort = availablePort(preferred: requestedPort)
        let requestedRuntime = env["CALENDAR_PILOT_RUNTIME_MODE"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        let now = ISO8601DateFormatter().string(from: Date())
        return CalendarPilotLaunchConfig(
            status: "launching",
            launchID: env["CALENDAR_PILOT_LAUNCH_ID"] ?? "launch_\(UUID().uuidString)",
            buildID: buildID,
            appBundlePath: bundleURL.path,
            appRoot: appRoot.path,
            runDir: runDir.path,
            staticDir: appRoot.appendingPathComponent("frontend/static", isDirectory: true).path,
            pythonExecutable: env["CALENDAR_PILOT_PYTHON"] ?? "/usr/bin/python3",
            host: env["CALENDAR_PILOT_HOST"] ?? "127.0.0.1",
            port: selectedPort,
            runtimeMode: requestedRuntime?.isEmpty == false ? requestedRuntime! : "auto",
            kernelServerPath: kernelPath,
            eventKitBridgePath: bridgePath,
            startedAt: now,
            launcherPID: ProcessInfo.processInfo.processIdentifier,
            serverPID: nil,
            updatedAt: now
        )
    }

    private static func availablePort(preferred: Int) -> Int {
        if portIsAvailable(preferred) {
            return preferred
        }
        let socket = socket(AF_INET, SOCK_STREAM, 0)
        guard socket >= 0 else {
            return preferred
        }
        defer { close(socket) }
        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = in_port_t(0).bigEndian
        address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))
        let bindResult = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPointer in
                bind(socket, sockaddrPointer, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bindResult == 0 else {
            return preferred
        }
        var chosen = sockaddr_in()
        var length = socklen_t(MemoryLayout<sockaddr_in>.size)
        let nameResult = withUnsafeMutablePointer(to: &chosen) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPointer in
                getsockname(socket, sockaddrPointer, &length)
            }
        }
        guard nameResult == 0 else {
            return preferred
        }
        return Int(in_port_t(bigEndian: chosen.sin_port))
    }

    private static func portIsAvailable(_ port: Int) -> Bool {
        let socket = socket(AF_INET, SOCK_STREAM, 0)
        guard socket >= 0 else {
            return false
        }
        defer { close(socket) }
        var reuse: Int32 = 1
        setsockopt(socket, SOL_SOCKET, SO_REUSEADDR, &reuse, socklen_t(MemoryLayout<Int32>.size))
        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = in_port_t(port).bigEndian
        address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))
        let result = withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPointer in
                bind(socket, sockaddrPointer, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        return result == 0
    }

    func writeManifest() throws {
        let runURL = URL(fileURLWithPath: runDir, isDirectory: true)
        try FileManager.default.createDirectory(at: runURL, withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(self)
        try data.write(to: runURL.appendingPathComponent("launch_state.json"), options: [.atomic])
    }
}

final class CalendarPilotProcessSupervisor {
    private var frontendProcess: Process?
    private let config: CalendarPilotLaunchConfig
    private var didStop = false

    init(config: CalendarPilotLaunchConfig) {
        self.config = config
    }

    func start() throws {
        try config.writeManifest()
        let runURL = URL(fileURLWithPath: config.runDir, isDirectory: true)
        try FileManager.default.createDirectory(at: runURL, withIntermediateDirectories: true)
        let stdout = runURL.appendingPathComponent("frontend.stdout.log")
        let stderr = runURL.appendingPathComponent("frontend.stderr.log")

        let process = Process()
        process.executableURL = URL(fileURLWithPath: config.pythonExecutable)
        process.currentDirectoryURL = URL(fileURLWithPath: config.appRoot, isDirectory: true)
        process.arguments = [
            "-m", "calendar_pilot.app", "frontend",
            "--serve",
            "--host", config.host,
            "--port", String(config.port),
            "--run-dir", config.runDir,
        ]
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = URL(fileURLWithPath: config.appRoot).appendingPathComponent("src").path
        env["CALENDAR_PILOT_RUNTIME_MODE"] = config.runtimeMode
        env["CALENDAR_PILOT_LAUNCH_ID"] = config.launchID
        env["CALENDAR_PILOT_LAUNCH_PORT"] = String(config.port)
        env["CALENDAR_PILOT_LAUNCH_REQUESTED_PORT"] = ProcessInfo.processInfo.environment["CALENDAR_PILOT_PORT"] ?? String(config.port)
        env["CALENDAR_PILOT_LAUNCHER_PID"] = String(config.launcherPID)
        env["CALENDAR_PILOT_APP_ROOT"] = config.appRoot
        env["CALENDAR_PILOT_RUN_DIR"] = config.runDir
        env["CALENDAR_PILOT_BUILD_ID"] = config.buildID
        env["CALENDAR_PILOT_SWIFT_KERNEL_SERVER"] = config.kernelServerPath
        env["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = config.eventKitBridgePath
        process.environment = env
        process.standardOutput = try FileHandle(forWritingTo: stdout, createIfNeeded: true)
        process.standardError = try FileHandle(forWritingTo: stderr, createIfNeeded: true)
        try process.run()
        frontendProcess = process
    }

    func stop() {
        guard !didStop, let process = frontendProcess else { return }
        didStop = true
        guard process.isRunning else {
            frontendProcess = nil
            return
        }
        process.terminate()
        let deadline = Date().addingTimeInterval(3.0)
        while process.isRunning && Date() < deadline {
            RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
        }
        if process.isRunning {
            Self.killDescendants(of: process.processIdentifier, signalNumber: SIGKILL)
            kill(process.processIdentifier, SIGKILL)
            process.waitUntilExit()
        }
        frontendProcess = nil
    }

    private static func killDescendants(of pid: Int32, signalNumber: Int32) {
        let descendants = descendantPIDs(of: pid)
        for child in descendants.reversed() {
            kill(child, signalNumber)
        }
    }

    private static func descendantPIDs(of pid: Int32) -> [Int32] {
        let directChildren = childPIDs(of: pid)
        var output = directChildren
        for child in directChildren {
            output.append(contentsOf: descendantPIDs(of: child))
        }
        return output
    }

    private static func childPIDs(of pid: Int32) -> [Int32] {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
        process.arguments = ["-P", String(pid)]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return []
        }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        guard let text = String(data: data, encoding: .utf8) else { return [] }
        return text
            .split(whereSeparator: { $0 == "\n" || $0 == " " || $0 == "\t" })
            .compactMap { Int32($0) }
    }
}

private extension FileHandle {
    convenience init(forWritingTo url: URL, createIfNeeded: Bool) throws {
        if createIfNeeded && !FileManager.default.fileExists(atPath: url.path) {
            FileManager.default.createFile(atPath: url.path, contents: nil)
        }
        try self.init(forWritingTo: url)
        try self.seekToEnd()
    }
}

final class CalendarPilotAppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private let config = CalendarPilotLaunchConfig.fromEnvironment()
    private var supervisor: CalendarPilotProcessSupervisor?
    private var window: NSWindow?
    private var webView: WKWebView?
    private var signalSources: [DispatchSourceSignal] = []
    private var pendingLoadAttempts = 0

    func applicationDidFinishLaunching(_ notification: Notification) {
        do {
            let supervisor = CalendarPilotProcessSupervisor(config: config)
            try supervisor.start()
            self.supervisor = supervisor
            openWindow()
        } catch {
            showFatalError(error)
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        supervisor?.stop()
    }

    func installTerminationHandler(_ signalNumber: Int32) {
        signal(signalNumber, SIG_IGN)
        let source = DispatchSource.makeSignalSource(signal: signalNumber, queue: .main)
        source.setEventHandler {
            Task { @MainActor in
                NSApp.terminate(nil)
            }
        }
        source.resume()
        signalSources.append(source)
    }

    private func openWindow() {
        let configuration = WKWebViewConfiguration()
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = true
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        self.webView = webView
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1280, height: 860),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "CalendarPilot"
        window.center()
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        self.window = window
        waitForServerAndLoad()
    }

    private func waitForServerAndLoad() {
        pendingLoadAttempts += 1
        var request = URLRequest(url: config.baseURL)
        request.timeoutInterval = 1.5
        URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
            DispatchQueue.main.async {
                guard let self = self, let webView = self.webView else { return }
                if let http = response as? HTTPURLResponse, 200..<500 ~= http.statusCode {
                    self.pendingLoadAttempts = 0
                    webView.load(URLRequest(url: self.config.baseURL))
                    return
                }
                if self.pendingLoadAttempts == 30 {
                    webView.loadHTMLString(
                        "<html><body style=\"font:14px -apple-system;padding:24px\">CalendarPilot is still starting. The app will load automatically when the backend is ready.</body></html>",
                        baseURL: nil
                    )
                }
                let retryDelay = self.pendingLoadAttempts < 300 ? 1.0 : 5.0
                DispatchQueue.main.asyncAfter(deadline: .now() + retryDelay) {
                    self.waitForServerAndLoad()
                }
            }
        }.resume()
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.waitForServerAndLoad()
        }
    }

    private func showFatalError(_ error: Error) {
        let alert = NSAlert()
        alert.messageText = "CalendarPilot failed to launch"
        alert.informativeText = String(describing: error)
        alert.alertStyle = .critical
        alert.runModal()
        NSApp.terminate(nil)
    }
}

@main
struct CalendarPilotMacApplication {
    static func main() {
        let app = NSApplication.shared
        let delegate = CalendarPilotAppDelegate()
        delegate.installTerminationHandler(SIGTERM)
        delegate.installTerminationHandler(SIGINT)
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.activate(ignoringOtherApps: true)
        app.run()
    }
}
#else
@main
struct CalendarPilotMacApplicationFallback {
    static func main() {
        print("CalendarPilotMacApp requires macOS AppKit/WebKit. Build the app bundle on macOS with scripts/build_macos_app.sh.")
    }
}
#endif
