import cv2
import numpy as np
import matplotlib.pyplot as plt

def extract_structure(image_path):
    # 1. Read Image
    img = cv2.imread(image_path)
    if img is None: return
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Binarize (Invert so lines are white)
    # Adaptive thresholding handles uneven lighting better
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # 3. Filter by "Connected Components" (Remove Text/Noise)
    # We remove small blobs (text) and keep only large connected shapes
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    
    cleaned_img = np.zeros_like(binary)
    
    # Heuristic: Keep components that are large enough (Beams)
    # You might need to tune 'min_area' based on your image resolution
    min_area = 100 
    for i in range(1, num_labels): # Start from 1 to ignore background
        area = stats[i, cv2.CC_STAT_AREA]
        if area > min_area:
            cleaned_img[labels == i] = 255

    # 4. Morphological Operations to remove "thin" dimension lines
    # (Optional: Only use if beams are distinctly thicker)
    kernel = np.ones((3,3), np.uint8)
    # closing fills small gaps
    cleaned_img = cv2.morphologyEx(cleaned_img, cv2.MORPH_CLOSE, kernel)
    
    # 5. Detect Lines (Probabilistic Hough)
    min_line_length = 50  # Ignore short lines (arrow heads, ticks)
    max_line_gap = 10     # Merge lines that are close
    lines = cv2.HoughLinesP(cleaned_img, 1, np.pi/180, threshold=50, 
                            minLineLength=min_line_length, maxLineGap=max_line_gap)

    # Visualization
    debug_img = img.copy()
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(debug_img, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # Plot results
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(binary, cmap='gray')
    axes[0].set_title("1. Raw Binary")
    axes[1].imshow(cleaned_img, cmap='gray')
    axes[1].set_title("2. Cleaned (No Text/Small Noise)")
    axes[2].imshow(cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB))
    axes[2].set_title("3. Detected Beams")
    plt.show()


if __name__ == "__main__":
    extract_structure("uploads\Screenshot_2025-09-01_113831.png")
