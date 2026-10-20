import Foundation
import Vision
import ImageIO
import CoreGraphics

// Korean/English OCR of locally saved official label images. Output is unverified.
let args = CommandLine.arguments
if args.count < 2 { fatalError("usage: ocr_labels image") }
let url = URL(fileURLWithPath: args[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL,nil), let full = CGImageSourceCreateImageAtIndex(src,0,nil) else { fatalError("image decode failed") }
var lines:[[String:Any]]=[]
let step=1800, tileHeight=2000
for top in stride(from:0,to:full.height,by:step) {
 let h=min(tileHeight,full.height-top)
 guard let crop=full.cropping(to:CGRect(x:0,y:top,width:full.width,height:h)) else {continue}
 let request=VNRecognizeTextRequest()
 request.usesCPUOnly = true
 request.recognitionLevel = .accurate
 request.recognitionLanguages = ["ko-KR","en-US"]
 request.usesLanguageCorrection = false
 try VNImageRequestHandler(cgImage:crop,options:[:]).perform([request])
 for obs in request.results ?? [] {
  guard let c=obs.topCandidates(1).first else {continue}
  let y=Double(top)+Double(h)*(1-obs.boundingBox.maxY)
  lines.append(["text":c.string,"confidence":Double(c.confidence),"x":obs.boundingBox.minX,"y":y,"tile_top":top])
 }
}
let sorted=lines.sorted { ($0["y"] as! Double) < ($1["y"] as! Double) }
let output:[String:Any] = ["method":"vision_ocr_pending_visual","width":full.width,"height":full.height,"lines":sorted]
let data=try JSONSerialization.data(withJSONObject:output,options:[.prettyPrinted,.sortedKeys,.withoutEscapingSlashes])
FileHandle.standardOutput.write(data)
