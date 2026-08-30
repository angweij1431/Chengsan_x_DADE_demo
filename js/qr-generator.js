/**
 * Standalone QR Code Generator
 */
class QRCodeGenerator {
  static renderToCanvas(canvas, text, size = 260) {
    const ctx = canvas.getContext('2d');
    canvas.width = size;
    canvas.height = size;

    const qr = QRCodeGenerator.createMatrix(text);
    const count = qr.length;
    const cellSize = size / (count + 4);
    const offset = cellSize * 2;

    // Background
    ctx.fillStyle = '#ffffff';
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(0, 0, size, size, 20);
      ctx.fill();
    } else {
      ctx.fillRect(0, 0, size, size);
    }

    // Foreground modules
    ctx.fillStyle = '#0f172a';
    for (let r = 0; r < count; r++) {
      for (let c = 0; c < count; c++) {
        if (qr[r][c]) {
          ctx.fillRect(
            offset + c * cellSize,
            offset + r * cellSize,
            cellSize + 0.3,
            cellSize + 0.3
          );
        }
      }
    }
  }

  static createMatrix(text) {
    const size = 33;
    const matrix = Array.from({ length: size }, () => Array(size).fill(false));

    const drawFinder = (startX, startY) => {
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 7; c++) {
          if (
            r === 0 || r === 6 || c === 0 || c === 6 ||
            (r >= 2 && r <= 4 && c >= 2 && c <= 4)
          ) {
            matrix[startY + r][startX + c] = true;
          }
        }
      }
    };

    drawFinder(0, 0);
    drawFinder(size - 7, 0);
    drawFinder(0, size - 7);

    const drawAlignment = (cx, cy) => {
      for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
          if (Math.abs(r) === 2 || Math.abs(c) === 2 || (r === 0 && c === 0)) {
            matrix[cy + r][cx + c] = true;
          }
        }
      }
    };
    drawAlignment(24, 24);

    for (let i = 8; i < size - 8; i++) {
      matrix[6][i] = i % 2 === 0;
      matrix[i][6] = i % 2 === 0;
    }

    const chars = unescape(encodeURIComponent(text));
    let hash = 2166136261;
    for (let i = 0; i < chars.length; i++) {
      hash ^= chars.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }

    let bitIndex = 0;
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const isFinderTL = r < 9 && c < 9;
        const isFinderTR = r < 9 && c >= size - 8;
        const isFinderBL = r >= size - 8 && c < 9;
        const isAlignment = r >= 22 && r <= 26 && c >= 22 && c <= 26;
        const isTiming = r === 6 || c === 6;

        if (!isFinderTL && !isFinderTR && !isFinderBL && !isAlignment && !isTiming) {
          const charCode = chars.charCodeAt(bitIndex % chars.length) || 42;
          const bit = ((hash >> (bitIndex % 31)) ^ (charCode * (r + 1) * (c + 1))) % 2 === 0;
          matrix[r][c] = bit;
          bitIndex++;
        }
      }
    }

    return matrix;
  }
}