import AppKit
import SwiftUI
import WebKit

@main
struct CalendarPilotMacApp: App {
    @StateObject private var server = FrontendServerController()

    var body: some Scene {
        WindowGroup("CalendarPilot") {
            ContentView()
                .environmentObject(server)
                .frame(minWidth: 1060, minHeight: 740)
                .onAppear {
                    server.start()
                }
        }
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Open In Browser") {
                    server.openInBrowser()
                }
                .disabled(server.frontendURL == nil)
            }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject private var server: FrontendServerController

    var body: some View {
        ZStack {
            if let url = server.frontendURL {
                CalendarPilotWebView(url: url)
            } else {
                VStack(alignment: .leading, spacing: 12) {
                    Text("CalendarPilot")
                        .font(.system(size: 24, weight: .bold))
                    Text(server.status)
                        .foregroundStyle(.secondary)
                    if let detail = server.detail {
                        Text(detail)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                    }
                    Button("Retry") {
                        server.start(force: true)
                    }
                }
                .padding(28)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
        .onDisappear {
            server.stop()
        }
    }
}

struct CalendarPilotWebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let preferences = WKWebpagePreferences()
        preferences.allowsContentJavaScript = true

        let configuration = WKWebViewConfiguration()
        configuration.defaultWebpagePreferences = preferences

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.allowsBackForwardNavigationGestures = true
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        if webView.url != url {
            webView.load(URLRequest(url: url))
        }
    }
}

@MainActor
final class FrontendServerController: ObservableObject {
    @Published var frontendURL: URL?
    @Published var status = "Starting local fixture-backed frontend..."
    @Published var detail: String?

    private var process: Process?
    private var port = 8787

    init() {
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.stop() }
        }
    }

    func start(force: Bool = false) {
        if process != nil && !force {
            return
        }
        stop()
        frontendURL = nil
        status = "Locating CalendarPilot frontend..."
        detail = nil

        guard let root = findFrontendRoot() else {
            status = "CalendarPilot frontend was not found."
            detail = "Set CALENDAR_PILOT_ROOT to the calendar-pilot-frontend directory, or rebuild the app bundle with scripts/build_macos_app.sh."
            return
        }

        guard let selectedPort = firstAvailablePort(startingAt: 8787, attempts: 25) else {
            status = "No local port is available."
            detail = "CalendarPilot tried ports 8787 through 8811 on 127.0.0.1."
            return
        }
        port = selectedPort
        status = "Starting local API server..."
        detail = root.path

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.currentDirectoryURL = root
        proc.arguments = [
            "python3",
            "-m",
            "calendar_pilot.app",
            "frontend",
            "--serve",
            "--host",
            "127.0.0.1",
            "--port",
            String(port),
            "--run-dir",
            "runs/macos-app",
        ]
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONPATH"] = "src"
        environment["PYTHONUNBUFFERED"] = "1"
        environment["CALENDAR_PILOT_ROOT"] = root.path
        proc.environment = environment

        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe
        proc.terminationHandler = { [weak self] process in
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data.suffix(4000), encoding: .utf8) ?? ""
            Task { @MainActor in
                if self?.process === process {
                    self?.process = nil
                    self?.frontendURL = nil
                    self?.status = "CalendarPilot server stopped."
                    self?.detail = output.isEmpty ? "Process exited with status \(process.terminationStatus)." : output
                }
            }
        }

        do {
            try proc.run()
            process = proc
        } catch {
            status = "Could not start Python frontend server."
            detail = error.localizedDescription
            return
        }

        waitForServer(port: port)
    }

    func stop() {
        guard let process else {
            return
        }
        process.terminate()
        self.process = nil
    }

    func openInBrowser() {
        guard let frontendURL else {
            return
        }
        NSWorkspace.shared.open(frontendURL)
    }

    private func waitForServer(port: Int) {
        status = "Waiting for local API server..."
        let url = URL(string: "http://127.0.0.1:\(port)/api/state")!
        Task.detached {
            for _ in 0..<80 {
                if (try? Data(contentsOf: url)) != nil {
                    await MainActor.run {
                        self.frontendURL = URL(string: "http://127.0.0.1:\(port)")!
                        self.status = "CalendarPilot is running."
                        self.detail = nil
                    }
                    return
                }
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
            await MainActor.run {
                self.status = "CalendarPilot API did not become ready."
                self.detail = "Check that python3 can run the bundled frontend package."
            }
        }
    }

    private func findFrontendRoot() -> URL? {
        let fm = FileManager.default
        let environment = ProcessInfo.processInfo.environment
        if let path = environment["CALENDAR_PILOT_ROOT"], isFrontendRoot(URL(fileURLWithPath: path)) {
            return URL(fileURLWithPath: path)
        }

        let cwd = URL(fileURLWithPath: fm.currentDirectoryPath)
        if isFrontendRoot(cwd) {
            return cwd
        }

        if let resource = Bundle.main.resourceURL?.appendingPathComponent("calendar-pilot-frontend"),
           isFrontendRoot(resource) {
            return resource
        }

        let bundleParent = Bundle.main.bundleURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        if isFrontendRoot(bundleParent) {
            return bundleParent
        }

        return nil
    }

    private func isFrontendRoot(_ url: URL) -> Bool {
        FileManager.default.fileExists(atPath: url.appendingPathComponent("src/calendar_pilot/app.py").path)
    }

    private func firstAvailablePort(startingAt start: Int, attempts: Int) -> Int? {
        for candidate in start..<(start + attempts) {
            if isPortAvailable(candidate) {
                return candidate
            }
        }
        return nil
    }

    private func isPortAvailable(_ port: Int) -> Bool {
        let socketFD = socket(AF_INET, SOCK_STREAM, 0)
        if socketFD < 0 {
            return false
        }
        defer { close(socketFD) }

        var yes: Int32 = 1
        setsockopt(socketFD, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))

        var address = sockaddr_in()
        address.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        address.sin_family = sa_family_t(AF_INET)
        address.sin_port = in_port_t(port).bigEndian
        address.sin_addr = in_addr(s_addr: inet_addr("127.0.0.1"))

        return withUnsafePointer(to: &address) { pointer in
            pointer.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockaddrPointer in
                bind(socketFD, sockaddrPointer, socklen_t(MemoryLayout<sockaddr_in>.size)) == 0
            }
        }
    }
}
