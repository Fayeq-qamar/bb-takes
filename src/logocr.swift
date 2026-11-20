// logocr: OCR log sheet images/PDF pages with Apple Vision. Prints JSON:
// [{"file":..., "page":n, "w":W, "h":H, "items":[{"t":text,"x":minX,"y":minY,"w":w,"h":h}]}]  (top-left origin, pixels)
import Foundation
import Vision
import AppKit
import PDFKit

func cgImages(_ path: String) -> [CGImage] {
    let url = URL(fileURLWithPath: path)
    if path.lowercased().hasSuffix(".pdf"), let doc = PDFDocument(url: url) {
        var out: [CGImage] = []
        for i in 0..<doc.pageCount {
            guard let page = doc.page(at: i) else { continue }
            let r = page.bounds(for: .mediaBox); let s: CGFloat = 3
            let img = NSImage(size: NSSize(width: r.width * s, height: r.height * s))
            img.lockFocus(); NSColor.white.set(); NSRect(x: 0, y: 0, width: r.width * s, height: r.height * s).fill()
            if let ctx = NSGraphicsContext.current?.cgContext { ctx.scaleBy(x: s, y: s); page.draw(with: .mediaBox, to: ctx) }
            img.unlockFocus()
            if let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) { out.append(cg) }
        }
        return out
    }
    guard let img = NSImage(contentsOf: url), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return [] }
    return [cg]
}

var results: [[String: Any]] = []
for path in CommandLine.arguments.dropFirst() {
    for (pi, cg) in cgImages(path).enumerated() {
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .accurate; req.usesLanguageCorrection = false
        let h = VNImageRequestHandler(cgImage: cg, options: [:])
        try? h.perform([req])
        let W = Double(cg.width), H = Double(cg.height)
        var items: [[String: Any]] = []
        for o in req.results ?? [] {
            guard let c = o.topCandidates(1).first else { continue }
            let b = o.boundingBox
            items.append(["t": c.string, "x": b.minX * W, "y": (1 - b.maxY) * H, "w": b.width * W, "h": b.height * H])
        }
        results.append(["file": path, "page": pi + 1, "w": W, "h": H, "items": items])
    }
}
let data = try! JSONSerialization.data(withJSONObject: results, options: [])
FileHandle.standardOutput.write(data)
