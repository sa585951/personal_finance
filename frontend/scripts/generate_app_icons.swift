import AppKit
import Foundation

let outputDirectory = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "public")

func color(_ red: CGFloat, _ green: CGFloat, _ blue: CGFloat) -> NSColor {
    NSColor(calibratedRed: red / 255, green: green / 255, blue: blue / 255, alpha: 1)
}

func renderIcon(size: Int, name: String) throws {
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    ), let context = NSGraphicsContext(bitmapImageRep: bitmap) else {
        throw NSError(domain: "NomicaIcon", code: 1)
    }

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    context.imageInterpolation = .high
    context.cgContext.setShouldAntialias(true)
    context.cgContext.scaleBy(x: CGFloat(size) / 1024, y: CGFloat(size) / 1024)

    let background = NSBezierPath(rect: NSRect(x: 0, y: 0, width: 1024, height: 1024))
    color(66, 99, 235).setFill()
    background.fill()

    let connector = NSBezierPath()
    connector.move(to: NSPoint(x: 286, y: 734))
    connector.line(to: NSPoint(x: 738, y: 290))
    connector.lineWidth = 90
    connector.lineCapStyle = .round
    color(76, 201, 192).setStroke()
    connector.stroke()

    let letter = NSBezierPath()
    letter.move(to: NSPoint(x: 286, y: 290))
    letter.line(to: NSPoint(x: 286, y: 734))
    letter.move(to: NSPoint(x: 738, y: 290))
    letter.line(to: NSPoint(x: 738, y: 734))
    letter.lineWidth = 100
    letter.lineCapStyle = .round
    color(255, 255, 255).setStroke()
    letter.stroke()

    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "NomicaIcon", code: 2)
    }
    try png.write(to: outputDirectory.appendingPathComponent(name))
}

try renderIcon(size: 512, name: "app-icon-512.png")
try renderIcon(size: 192, name: "app-icon-192.png")
try renderIcon(size: 180, name: "apple-touch-icon.png")
try renderIcon(size: 32, name: "favicon.png")
try renderIcon(size: 640, name: "nomica-line-profile-640.png")

// ICO embeds the same 32px PNG so the browser fallback keeps the current mark.
let favicon = try Data(contentsOf: outputDirectory.appendingPathComponent("favicon.png"))
var ico = Data([0, 0, 1, 0, 1, 0, 32, 32, 0, 0, 1, 0, 32, 0])
for value in [UInt32(favicon.count), UInt32(22)] {
    for shift in stride(from: 0, through: 24, by: 8) {
        ico.append(UInt8((value >> shift) & 0xff))
    }
}
ico.append(favicon)
try ico.write(to: outputDirectory.appendingPathComponent("favicon.ico"))
