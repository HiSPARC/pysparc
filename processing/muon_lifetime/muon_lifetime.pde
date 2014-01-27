JSONObject json;
JSONArray data;


int N = 31;
int NB = 32;
// int N = 10;
float DT = NB * 6.25;

int margin = 50;
int px0;
int px1;
int py0;
int py1;
int max_n = 200;
float max_bin = (N - 1) * DT;


void setup() {
  size(600, 400);
  frameRate(1);
  
  px0 = margin;
  px1 = width - margin;
  py0 = margin;
  py1 = height - margin;
}

void draw() {
  json = loadJSONObject("http://127.0.0.1:5000/data");
  data = json.getJSONArray("lifetime_data");
  
  background(0);
  
  draw_histogram(data);
}

void draw_histogram(JSONArray data) {
  int i, idx;
  int x, y, px, py;
  
  // empty histogram data
  float[] bins = new float[N];
  float[] n = new float[N];
  for (i = 0; i < N; i ++) {
    bins[i] = i * DT;
    n[i] = 0;
  }
  
  // fill histogram
  for (i = 0; i < data.size(); i ++) {
    idx = searchsorted(data.getFloat(i), bins);
    n[idx] ++;
  }
  
  // draw histogram
  stroke(255);
  noFill();
  rectMode(CORNERS);
  rect(px0, py0, px1, py1);
  px = px0;
  py = round(map(n[0], 0, max_n, py1, py0));
  for (i = 0; i < N; i ++) {
   y = round(map(n[i], 0, max_n, py1, py0));
   x = round(map(bins[i], 0, max_bin, px0, px1));
   line(px, py, x, py);
   line(x, py, x, y);
   px = x;
   py = y;
  }
  line(px, py, px1, py);
}

int searchsorted(float value, float[] bins) {
  int i;
  for (i = 1; i < N; i ++) {
    if (value < bins[i]) {
      return i - 1;
    }
  }
  return i - 1;
}
