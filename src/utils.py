import cv2


def draw_overlays(frame, boxes, text, color, frame_id=None):
    """Desenha boxes e textos no frame"""
    if frame_id is not None:
        cv2.putText(frame, f"Frame {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    for item in boxes:
        if len(item) == 5:
            x1, y1, x2, y2, conf = item
            dist_m = None
            width_m = None
        else:
            x1, y1, x2, y2, conf, dist_m, width_m = item
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        if dist_m is not None and width_m is not None:
            label = f"Buraco {conf:.2f} | {dist_m:.1f}m | L~{width_m:.2f}m"
        elif dist_m is not None:
            label = f"Buraco {conf:.2f} | {dist_m:.1f}m"
        else:
            label = f"Buraco {conf:.2f}"
        
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    if text:
        cv2.putText(frame, text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return frame
