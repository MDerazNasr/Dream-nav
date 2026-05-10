import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const outputPath = join(process.cwd(), "data/scenes/warehouse_01/splat.ply");

const splats = [
  { position: [-0.7, 1.35, -1.2], color: [1.3, -0.5, -0.5], scale: 0.18 },
  { position: [-0.25, 1.55, -1.35], color: [-0.4, 1.1, -0.4], scale: 0.2 },
  { position: [0.2, 1.35, -1.55], color: [-0.5, -0.3, 1.3], scale: 0.18 },
  { position: [0.65, 1.6, -1.7], color: [1.2, 0.7, -0.4], scale: 0.22 },
  { position: [0.1, 1.0, -2.05], color: [0.9, 0.9, 0.9], scale: 0.26 },
  { position: [-0.55, 0.9, -1.85], color: [0.4, 1.0, 0.9], scale: 0.16 }
];

const properties = [
  "x",
  "y",
  "z",
  "f_dc_0",
  "f_dc_1",
  "f_dc_2",
  "opacity",
  "scale_0",
  "scale_1",
  "scale_2",
  "rot_0",
  "rot_1",
  "rot_2",
  "rot_3"
];

const header = [
  "ply",
  "format binary_little_endian 1.0",
  `element vertex ${splats.length}`,
  ...properties.map((property) => `property float ${property}`),
  "end_header\n"
].join("\n");

const rowBytes = properties.length * 4;
const data = Buffer.alloc(splats.length * rowBytes);

splats.forEach((splat, rowIndex) => {
  const scale = Math.log(splat.scale);
  const values = [
    ...splat.position,
    ...splat.color,
    4,
    scale,
    scale,
    scale,
    0,
    0,
    0,
    1
  ];

  values.forEach((value, valueIndex) => {
    data.writeFloatLE(value, rowIndex * rowBytes + valueIndex * 4);
  });
});

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, Buffer.concat([Buffer.from(header, "utf8"), data]));
