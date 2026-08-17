# trilateration.py

class Kalman2D:
    def __init__(self, dt=0.10, q=0.12, r=1.1):
        self.dt, self.q, self.r = dt, q, r
        self.state = [0.0, 0.0, 0.0, 0.0]
        self.P = [[1.0,0,0,0], [0,1.0,0,0], [0,0,1.0,0], [0,0,0,1.0]]
        self.initialized = False
        
    def predict(self):
        if not self.initialized: return
        self.state[0] += self.state[2] * self.dt; self.state[1] += self.state[3] * self.dt
        for i in range(4): self.P[i][i] += self.q
        
    def update(self, mx, my):
        if not self.initialized:
            self.state = [mx, my, 0.0, 0.0]; self.initialized = True; return mx, my
        Kx, Ky = self.P[0][0] / (self.P[0][0] + self.r), self.P[1][1] / (self.P[1][1] + self.r)
        old_x, old_y = self.state[0], self.state[1]
        self.state[0] += Kx * (mx - self.state[0]); self.state[1] += Ky * (my - self.state[1])
        self.state[2] = (self.state[0] - old_x) / self.dt; self.state[3] = (self.state[1] - old_y) / self.dt
        self.P[0][0] *= (1 - Kx); self.P[1][1] *= (1 - Ky)
        return self.state[0], self.state[1]

def trilaterate_2d(anchor_positions, distances):
    valid = [(p[0], p[1], d) for p, d in zip(anchor_positions, distances) if p is not None and 0.05 < d < 50.0]
    if len(valid) < 3: return None
    xr, yr, rr = valid[-1]
    A, b = [], []
    for xi, yi, ri in valid[:-1]:
        A.append((2 * (xi - xr), 2 * (yi - yr)))
        b.append(ri**2 - rr**2 - xi**2 + xr**2 - yi**2 + yr**2)
    if len(A) < 2: return None
    m00 = sum(ax * ax for ax, ay in A); m01 = sum(ax * ay for ax, ay in A); m11 = sum(ay * ay for ax, ay in A)
    v0  = sum(ax * bi for (ax, ay), bi in zip(A, b)); v1  = sum(ay * bi for (ax, ay), bi in zip(A, b))
    det = m00 * m11 - m01 * m01
    if abs(det) < 1e-9: return None
    return (-(v0 * m11 - v1 * m01) / det, -(m00 * v1 - m01 * v0) / det)