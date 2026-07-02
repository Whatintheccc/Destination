import AppKit
import Darwin
import SwiftUI
import WebKit

@main
struct CalendarPilotMacApp: App {
    @StateObject private var launcher = LauncherController()

    var body: some Scene {
        WindowGroup("CalendarPilot") {
            ContentView()
                .environmentObject(launcher)
                .frame(minWidth: 1120, minHeight: 760)
                .task {
                    launcher.start()
                }
        }
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Open In Browser") {
                    launcher.openInBrowser()
                }
                .disabled(launcher.frontendURL == nil)
                Button("Reload") {
                    launcher.reload()
                }
                .disabled(launcher.frontendURL == nil)
            }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject private var launcher: LauncherController

    var body: some View {
        ZStack {
            if let url = launcher.frontendURL {
                CalendarPilotWebView(url: url, reloadToken: launcher.reloadToken)
            } else {
                VStack(alignment: .leading, spacing: 14) {
                    Text("CalendarPilot")
                        .font(.system(size: 24, weight: .semibold))
                    Text(launcher.status)
                        .foregroundStyle(.secondary)
                    if let detail = launcher.detail {
                        Text(detail)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                            .foregroundStyle(.secondary)
                    }
                    if launcher.canRetry {
                        Button("Retry") {
                            launcher.start(force: true)
                        }
                    }
                }
                .padding(28)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
    }
}

struct CalendarPilotWebView: NSViewRepresentable {
    let url: URL
    let reloadToken: Int

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WKWebView {
        let preferences = WKWebpagePreferences()
        preferences.allowsContentJavaScript = true

        let configuration = WKWebViewConfiguration()
        configuration.defaultWebpagePreferences = preferences

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.allowsBackForwardNavigationGestures = true
        webView.uiDelegate = context.coordinator
        webView.load(URLRequest(url: url))
        context.coordinator.lastReloadToken = reloadToken
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        if webView.url != url {
            webView.load(URLRequest(url: url))
        } else if context.coordinator.lastReloadToken != reloadToken {
            context.coordinator.lastReloadToken = reloadToken
            webView.reload()
        }
    }

    @MainActor
    final class Coordinator: NSObject, WKUIDelegate {
        var lastReloadToken = 0

        func webView(
            _ webView: WKWebView,
            runJavaScriptAlertPanelWithMessage message: String,
            initiatedByFrame frame: WKFrameInfo,
            completionHandler: @escaping @MainActor @Sendable () -> Void
        ) {
            let alert = NSAlert()
            alert.messageText = message
            alert.addButton(withTitle: "OK")
            alert.runModal()
            completionHandler()
        }

        func webView(
            _ webView: WKWebView,
            runJavaScriptConfirmPanelWithMessage message: String,
            initiatedByFrame frame: WKFrameInfo,
            completionHandler: @escaping @MainActor @Sendable (Bool) -> Void
        ) {
            let alert = NSAlert()
            alert.messageText = message
            alert.addButton(withTitle: "OK")
            alert.addButton(withTitle: "Cancel")
            completionHandler(alert.runModal() == .alertFirstButtonReturn)
        }

        func webView(
            _ webView: WKWebView,
            runJavaScriptTextInputPanelWithPrompt prompt: String,
            defaultText: String?,
            initiatedByFrame frame: WKFrameInfo,
            completionHandler: @escaping @MainActor @Sendable (String?) -> Void
        ) {
            let alert = NSAlert()
            alert.messageText = prompt
            let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 360, height: 24))
            input.stringValue = defaultText ?? ""
            alert.accessoryView = input
            alert.addButton(withTitle: "OK")
            alert.addButton(withTitle: "Cancel")
            completionHandler(alert.runModal() == .alertFirstButtonReturn ? input.stringValue : nil)
        }
    }
}

@MainActor
final class LauncherController: ObservableObject {
    @Published var frontendURL: URL?
    @Published var status = "Starting CalendarPilot..."
    @Published var detail: String?
    @Published var canRetry = false
    @Published var reloadToken = 0

    private var process: Process?
    private var logHandle: FileHandle?
    private var signalSources: [DispatchSourceSignal] = []
    private var didOpenExternalBrowser = false
    private let environment = ProcessInfo.processInfo.environment

    init() {
        installSignalHandlers()
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.stop()
            }
        }
    }

    func start(force: Bool = false) {
        if process != nil && !force {
            return
        }
        stop()
        frontendURL = nil
        canRetry = false
        didOpenExternalBrowser = false
        status = "Preparing local runtime..."
        detail = nil

        guard let appRoot = resolveAppRoot() else {
            fail("Bundled app resources were not found.", detail: "Set CALENDAR_PILOT_APP_ROOT or rebuild the app bundle.")
            return
        }
        guard FileManager.default.fileExists(atPath: appRoot.appendingPathComponent("src/calendar_pilot/app.py").path) else {
            fail("Bundled Python source is missing.", detail: appRoot.path)
            return
        }

        let runDirectory = resolveRunDirectory()
        do {
            try FileManager.default.createDirectory(at: runDirectory, withIntermediateDirectories: true)
            logHandle = try openLogFile(runDirectory.appendingPathComponent("CalendarPilotLauncher.log"))
        } catch {
            fail("CalendarPilot could not prepare its run directory.", detail: error.localizedDescription)
            return
        }

        let host = environment["CALENDAR_PILOT_HOST"] ?? "127.0.0.1"
        let port = environment["CALENDAR_PILOT_PORT"] ?? "8787"
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.currentDirectoryURL = appRoot
        proc.arguments = [
            "python3",
            "-m",
            "calendar_pilot.frontend.launcher",
            "--app-root",
            appRoot.path,
            "--host",
            host,
            "--port",
            port,
            "--run-dir",
            runDirectory.path,
        ]

        var procEnvironment = environment
        procEnvironment["CALENDAR_PILOT_APP_ROOT"] = appRoot.path
        procEnvironment["CALENDAR_PILOT_HOST"] = host
        procEnvironment["CALENDAR_PILOT_PORT"] = port
        procEnvironment["CALENDAR_PILOT_RUN_DIR"] = runDirectory.path
        procEnvironment["CALENDAR_PILOT_OPEN_BROWSER"] = "0"
        procEnvironment["PYTHONPATH"] = appRoot.appendingPathComponent("src").path
        procEnvironment["PYTHONUNBUFFERED"] = "1"
        if FileManager.default.isExecutableFile(atPath: appRoot.appendingPathComponent("bin/CalendarPilotKernelServer").path) {
            procEnvironment["CALENDAR_PILOT_SWIFT_KERNEL_SERVER"] = appRoot.appendingPathComponent("bin/CalendarPilotKernelServer").path
        }
        let bundledBridgeApp = appRoot.appendingPathComponent("bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge")
        let bundledBridge = appRoot.appendingPathComponent("bin/CalendarPilotEventKitBridge")
        if FileManager.default.isExecutableFile(atPath: bundledBridgeApp.path) {
            procEnvironment["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = bundledBridgeApp.path
        } else if FileManager.default.isExecutableFile(atPath: bundledBridge.path) {
            procEnvironment["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = bundledBridge.path
        }
        proc.environment = procEnvironment
        proc.standardOutput = logHandle
        proc.standardError = logHandle
        proc.terminationHandler = { [weak self] process in
            Task { @MainActor in
                self?.launcherExited(process)
            }
        }

        do {
            try proc.run()
            process = proc
            status = "Waiting for local API..."
            detail = "Run state: \(runDirectory.path)"
            waitForLaunchState(in: runDirectory, process: proc)
        } catch {
            closeLogFile()
            fail("Could not start the CalendarPilot launcher.", detail: error.localizedDescription)
        }
    }

    func stop() {
        guard let process else {
            closeLogFile()
            return
        }
        if process.isRunning {
            process.terminate()
            let deadline = Date().addingTimeInterval(12)
            while process.isRunning && Date() < deadline {
                RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
            }
            if process.isRunning {
                Darwin.kill(process.processIdentifier, SIGKILL)
                process.waitUntilExit()
            }
        }
        self.process = nil
        closeLogFile()
    }

    func openInBrowser() {
        guard let frontendURL else {
            return
        }
        NSWorkspace.shared.open(frontendURL)
    }

    func reload() {
        reloadToken += 1
    }

    private func waitForLaunchState(in runDirectory: URL, process: Process) {
        let stateURL = runDirectory.appendingPathComponent("launch_state.json")
        Task.detached {
            let deadline = Date().addingTimeInterval(25)
            var lastDetail = "No launch state has been written yet."
            while Date() < deadline {
                if !process.isRunning {
                    await self.failFromTask("CalendarPilot exited before it became ready.", detail: "Exit status \(process.terminationStatus). \(lastDetail)")
                    return
                }
                if let state = Self.readJSON(stateURL) {
                    let status = state["status"] as? String ?? ""
                    lastDetail = Self.describeState(state)
                    if status == "running", let baseURL = state["base_url"] as? String, let url = URL(string: baseURL) {
                        if await Self.healthResponds(at: url) {
                            await self.launchReady(url: url)
                            return
                        }
                    } else if status == "failed" || status == "stopped" {
                        await self.failFromTask("CalendarPilot launch \(status).", detail: lastDetail)
                        return
                    }
                }
                try? await Task.sleep(nanoseconds: 150_000_000)
            }
            await self.failFromTask("CalendarPilot API did not become ready.", detail: lastDetail)
        }
    }

    private func launchReady(url: URL) {
        frontendURL = url
        status = "CalendarPilot is running."
        detail = nil
        canRetry = false
        if shouldOpenExternalBrowser(), !didOpenExternalBrowser {
            didOpenExternalBrowser = true
            NSWorkspace.shared.open(url)
        }
    }

    private func launcherExited(_ terminatedProcess: Process) {
        guard process === terminatedProcess else {
            return
        }
        closeLogFile()
        process = nil
        if frontendURL != nil {
            frontendURL = nil
            status = "CalendarPilot stopped."
            detail = "Exit status \(terminatedProcess.terminationStatus)."
            canRetry = true
        }
    }

    private func fail(_ message: String, detail: String?) {
        status = message
        self.detail = detail
        canRetry = true
    }

    private func failFromTask(_ message: String, detail: String?) {
        stop()
        fail(message, detail: detail)
    }

    private func resolveAppRoot() -> URL? {
        if let path = environment["CALENDAR_PILOT_APP_ROOT"], !path.isEmpty {
            return URL(fileURLWithPath: path).standardizedFileURL
        }
        if let resourceURL = Bundle.main.resourceURL {
            return resourceURL.appendingPathComponent("app", isDirectory: true).standardizedFileURL
        }
        return nil
    }

    private func resolveRunDirectory() -> URL {
        if let path = environment["CALENDAR_PILOT_RUN_DIR"], !path.isEmpty {
            return URL(fileURLWithPath: path).standardizedFileURL
        }
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Library/Application Support", isDirectory: true)
        return base.appendingPathComponent("CalendarPilot", isDirectory: true)
    }

    private func openLogFile(_ url: URL) throws -> FileHandle {
        FileManager.default.createFile(atPath: url.path, contents: nil)
        let handle = try FileHandle(forWritingTo: url)
        try handle.truncate(atOffset: 0)
        return handle
    }

    private func closeLogFile() {
        try? logHandle?.close()
        logHandle = nil
    }

    private func shouldOpenExternalBrowser() -> Bool {
        (environment["CALENDAR_PILOT_OPEN_BROWSER"] ?? "1") != "0"
    }

    private func installSignalHandlers() {
        for signalNumber in [SIGTERM, SIGINT] {
            signal(signalNumber, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: signalNumber, queue: .main)
            source.setEventHandler { [weak self] in
                self?.stop()
                NSApplication.shared.terminate(nil)
            }
            source.resume()
            signalSources.append(source)
        }
    }

    nonisolated private static func readJSON(_ url: URL) -> [String: Any]? {
        guard let data = try? Data(contentsOf: url) else {
            return nil
        }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    nonisolated private static func healthResponds(at baseURL: URL) async -> Bool {
        guard let healthURL = URL(string: "/api/health", relativeTo: baseURL) else {
            return false
        }
        var request = URLRequest(url: healthURL)
        request.timeoutInterval = 3
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    nonisolated private static func describeState(_ state: [String: Any]) -> String {
        let status = state["status"] as? String ?? "unknown"
        let reason = state["reason"] as? String ?? ""
        let baseURL = state["base_url"] as? String ?? ""
        let serverPID = state["server_pid"].map { "\($0)" } ?? "unknown"
        return "status=\(status) base_url=\(baseURL) server_pid=\(serverPID) reason=\(reason)"
    }
}
