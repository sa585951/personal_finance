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
    color(18, 73, 64).setFill()
    background.fill()

    let letter = NSBezierPath()
    letter.move(to: NSPoint(x: 262, y: 286))
    letter.line(to: NSPoint(x: 262, y: 738))
    letter.line(to: NSPoint(x: 762, y: 286))
    letter.line(to: NSPoint(x: 762, y: 738))
    letter.lineWidth = 102
    letter.lineCapStyle = .round
    letter.lineJoinStyle = .round
    color(247, 248, 244).setStroke()
    letter.stroke()

    let accent = NSBezierPath(ovalIn: NSRect(x: 704, y: 680, width: 116, height: 116))
    color(216, 164, 109).setFill()
    accent.fill()

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
