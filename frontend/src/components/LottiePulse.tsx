import Lottie from "lottie-react";

const pulseData = {
  v: "5.7.4",
  fr: 30,
  ip: 0,
  op: 60,
  w: 100,
  h: 100,
  nm: "pulse",
  ddd: 0,
  assets: [] as unknown[],
  layers: [
    {
      ddd: 0,
      ind: 1,
      ty: 4,
      nm: "circle",
      sr: 1,
      ks: {
        o: { a: 0, k: 100, ix: 11 },
        r: { a: 0, k: 0, ix: 10 },
        p: { a: 0, k: [50, 50, 0], ix: 2 },
        a: { a: 0, k: [0, 0, 0], ix: 1 },
        s: {
          a: 1,
          k: [
            { i: { x: [0.667, 0.667, 0.667], y: [1, 1, 1] }, o: { x: [0.333, 0.333, 0.333], y: [0, 0, 0] }, t: 0, s: [0, 0, 100] },
            { i: { x: [0.667, 0.667, 0.667], y: [1, 1, 1] }, o: { x: [0.333, 0.333, 0.333], y: [0, 0, 0] }, t: 30, s: [125, 125, 100] },
            { t: 60, s: [100, 100, 100] },
          ],
          ix: 6,
        },
      },
      ao: 0,
      shapes: [
        { ty: "el", p: { a: 0, k: [0, 0], ix: 3 }, s: { a: 0, k: [40, 40], ix: 4 }, d: 1, nm: "Ellipse Path 1", mn: "ADBE Vector Shape - Ellipse", hd: false },
        { ty: "fl", c: { a: 0, k: [0.1647, 0.702, 0.7216, 1], ix: 4 }, o: { a: 0, k: 100, ix: 5 }, r: 1, nm: "Fill 1", mn: "ADBE Vector Graphic - Fill", hd: false },
      ],
      ip: 0,
      op: 60,
      st: 0,
      bm: 0,
    },
  ],
};

export function LottiePulse() {
  return <Lottie animationData={pulseData} loop autoplay style={{ width: 56, height: 56 }} />;
}
