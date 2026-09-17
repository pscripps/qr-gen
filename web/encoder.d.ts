declare namespace qrcodegen {
  class QrCode {
    readonly size: number;
    static Ecc: { LOW: object };
    static encodeSegments(
      segments: unknown[],
      ecc: object,
      minVersion?: number,
      maxVersion?: number,
      mask?: number,
      boostEcl?: boolean,
    ): QrCode;
    getModule(x: number, y: number): boolean;
  }
  class QrSegment {
    static makeBytes(bytes: number[]): unknown;
  }
}
