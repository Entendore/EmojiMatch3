use eframe::egui;
use rand::seq::SliceRandom;
use rand::thread_rng;

const BOARD_SIZE: usize = 8;
const CELL_SIZE: f32 = 60.0;
const EMOJIS: &[&str] = &["🍎", "🍊", "🍇", "🍓", "🍋", "🥝", "🍒", "🫐"];
const EMPTY: usize = 99;

#[derive(Clone, Copy, PartialEq)]
struct Cell {
    emoji: usize,
    anim_offset: f32,
}

#[derive(Clone)]
struct Match3Game {
    board: [[Cell; BOARD_SIZE]; BOARD_SIZE],
    score: u32,
    moves: u32,
    selected_pos: Option<(usize, usize)>,
    animating: bool,
    anim_timer: f32,
    last_match_count: usize,
    game_over: bool,
    particles: Vec<Particle>,
}

#[derive(Clone, Copy)]
struct Particle {
    x: f32,
    y: f32,
    vx: f32,
    vy: f32,
    life: f32,
    emoji: usize,
    color: egui::Color32,
}

impl Match3Game {
    fn new() -> Self {
        let mut game = Match3Game {
            board: [[Cell { emoji: 0, anim_offset: 0.0 }; BOARD_SIZE]; BOARD_SIZE],
            score: 0,
            moves: 0,
            selected_pos: None,
            animating: false,
            anim_timer: 0.0,
            last_match_count: 0,
            game_over: false,
            particles: Vec::new(),
        };
        game.fill_board();
        while !game.find_matches().is_empty() {
            game.fill_board();
        }
        game
    }

    fn fill_board(&mut self) {
        let mut rng = thread_rng();
        let indices: Vec<usize> = (0..EMOJIS.len()).collect();
        for y in 0..BOARD_SIZE {
            for x in 0..BOARD_SIZE {
                self.board[y][x].emoji = *indices.choose(&mut rng).unwrap();
                self.board[y][x].anim_offset = 0.0;
            }
        }
    }

    fn find_matches(&self) -> Vec<(usize, usize)> {
        let mut matched = [[false; BOARD_SIZE]; BOARD_SIZE];

        for y in 0..BOARD_SIZE {
            let mut x = 0;
            while x < BOARD_SIZE - 2 {
                let emoji = self.board[y][x].emoji;
                if emoji == EMPTY { x += 1; continue; }
                let mut count = 1;
                let mut xx = x + 1;
                while xx < BOARD_SIZE && self.board[y][xx].emoji == emoji {
                    count += 1;
                    xx += 1;
                }
                if count >= 3 {
                    for i in x..xx { matched[y][i] = true; }
                }
                x = xx;
            }
        }

        for x in 0..BOARD_SIZE {
            let mut y = 0;
            while y < BOARD_SIZE - 2 {
                let emoji = self.board[y][x].emoji;
                if emoji == EMPTY { y += 1; continue; }
                let mut count = 1;
                let mut yy = y + 1;
                while yy < BOARD_SIZE && self.board[yy][x].emoji == emoji {
                    count += 1;
                    yy += 1;
                }
                if count >= 3 {
                    for i in y..yy { matched[i][x] = true; }
                }
                y = yy;
            }
        }

        let mut matches = Vec::new();
        for y in 0..BOARD_SIZE {
            for x in 0..BOARD_SIZE {
                if matched[y][x] { matches.push((x, y)); }
            }
        }
        matches
    }

    fn remove_matches(&mut self, matches: &[(usize, usize)]) {
        for &(x, y) in matches {
            self.spawn_particles(x, y, self.board[y][x].emoji);
            self.board[y][x].emoji = EMPTY;
        }
    }

    fn spawn_particles(&mut self, x: usize, y: usize, emoji: usize) {
        let colors = [
            egui::Color32::from_rgb(255, 100, 100),
            egui::Color32::from_rgb(255, 165, 0),
            egui::Color32::from_rgb(147, 112, 219),
            egui::Color32::from_rgb(255, 105, 180),
            egui::Color32::from_rgb(255, 255, 0),
            egui::Color32::from_rgb(144, 238, 144),
            egui::Color32::from_rgb(220, 20, 60),
            egui::Color32::from_rgb(65, 105, 225),
        ];
        let base_x = x as f32 * CELL_SIZE + CELL_SIZE / 2.0;
        let base_y = y as f32 * CELL_SIZE + CELL_SIZE / 2.0;
        for _ in 0..8 {
            let angle = rand::random::<f32>() * std::f32::consts::TAU;
            let speed = 2.0 + rand::random::<f32>() * 3.0;
            self.particles.push(Particle {
                x: base_x,
                y: base_y,
                vx: angle.cos() * speed,
                vy: angle.sin() * speed,
                life: 1.0,
                emoji,
                color: colors[emoji % colors.len()],
            });
        }
    }

    fn apply_gravity(&mut self) {
        let mut rng = thread_rng();
        let indices: Vec<usize> = (0..EMOJIS.len()).collect();

        for x in 0..BOARD_SIZE {
            let mut write_y = BOARD_SIZE - 1;
            for y in (0..BOARD_SIZE).rev() {
                if self.board[y][x].emoji != EMPTY {
                    self.board[write_y][x] = self.board[y][x];
                    if write_y != y {
                        self.board[y][x].emoji = EMPTY;
                    }
                    write_y = write_y.saturating_sub(1);
                }
            }
            for y in 0..=write_y {
                self.board[y][x].emoji = *indices.choose(&mut rng).unwrap();
                self.board[y][x].anim_offset = CELL_SIZE * (write_y - y + 1) as f32;
            }
        }
    }

    fn process_matches(&mut self) -> bool {
        let matches = self.find_matches();
        if matches.is_empty() { return false; }
        self.last_match_count = matches.len();
        self.score += matches.len() as u32 * 10;
        if matches.len() >= 4 { self.score += 50; }
        if matches.len() >= 5 { self.score += 100; }
        self.remove_matches(&matches);
        self.apply_gravity();
        true
    }

    fn swap(&mut self, pos1: (usize, usize), pos2: (usize, usize)) -> bool {
        let (x1, y1) = pos1;
        let (x2, y2) = pos2;
        let dx = (x1 as i32 - x2 as i32).abs();
        let dy = (y1 as i32 - y2 as i32).abs();
        if dx + dy != 1 { return false; }

        let temp = self.board[y1][x1].emoji;
        self.board[y1][x1].emoji = self.board[y2][x2].emoji;
        self.board[y2][x2].emoji = temp;

        let matches = self.find_matches();
        if matches.is_empty() {
            let temp = self.board[y1][x1].emoji;
            self.board[y1][x1].emoji = self.board[y2][x2].emoji;
            self.board[y2][x2].emoji = temp;
            false
        } else {
            self.moves += 1;
            self.animating = true;
            self.anim_timer = 0.0;
            self.process_matches();
            true
        }
    }

    fn update_animations(&mut self, dt: f32) {
        let mut still_animating = false;
        for y in 0..BOARD_SIZE {
            for x in 0..BOARD_SIZE {
                if self.board[y][x].anim_offset > 0.0 {
                    self.board[y][x].anim_offset -= dt * 400.0;
                    if self.board[y][x].anim_offset < 0.0 {
                        self.board[y][x].anim_offset = 0.0;
                    } else {
                        still_animating = true;
                    }
                }
            }
        }

        self.particles.retain_mut(|p| {
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.15;
            p.life -= dt * 2.0;
            p.life > 0.0
        });

        if still_animating {
            self.anim_timer += dt;
        } else if self.animating {
            self.animating = false;
            if self.process_matches() {
                self.animating = true;
            }
        }
    }

    fn has_valid_moves(&self) -> bool {
        for y in 0..BOARD_SIZE {
            for x in 0..BOARD_SIZE {
                if x + 1 < BOARD_SIZE {
                    let mut temp = self.clone();
                    let e1 = temp.board[y][x].emoji;
                    let e2 = temp.board[y][x+1].emoji;
                    temp.board[y][x].emoji = e2;
                    temp.board[y][x+1].emoji = e1;
                    if !temp.find_matches().is_empty() { return true; }
                }
                if y + 1 < BOARD_SIZE {
                    let mut temp = self.clone();
                    let e1 = temp.board[y][x].emoji;
                    let e2 = temp.board[y+1][x].emoji;
                    temp.board[y][x].emoji = e2;
                    temp.board[y+1][x].emoji = e1;
                    if !temp.find_matches().is_empty() { return true; }
                }
            }
        }
        false
    }
}

struct Match3App {
    game: Match3Game,
    high_score: u32,
    show_hint: bool,
}

impl Default for Match3App {
    fn default() -> Self {
        Self {
            game: Match3Game::new(),
            high_score: 0,
            show_hint: false,
        }
    }
}

impl eframe::App for Match3App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        ctx.request_repaint_after(std::time::Duration::from_millis(16));
        self.game.update_animations(ctx.input(|i| i.stable_dt));

        if self.game.score > self.high_score {
            self.high_score = self.game.score;
        }

        egui::CentralPanel::default()
            .frame(egui::Frame::default().fill(egui::Color32::from_rgb(30, 30, 40)))
            .show(ctx, |ui| {
                ui.vertical_centered(|ui| {
                    ui.add_space(10.0);
                    ui.heading(egui::RichText::new("🎮 Match-3 Emoji Game 🎮")
                        .size(32.0)
                        .color(egui::Color32::from_rgb(255, 215, 0)));
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.add_space(20.0);
                        ui.label(egui::RichText::new(format!("⭐ Score: {}", self.game.score))
                            .size(18.0)
                            .color(egui::Color32::WHITE));
                        ui.add_space(30.0);
                        ui.label(egui::RichText::new(format!("🎯 Moves: {}", self.game.moves))
                            .size(18.0)
                            .color(egui::Color32::WHITE));
                        ui.add_space(30.0);
                        ui.label(egui::RichText::new(format!("🏆 High: {}", self.high_score))
                            .size(18.0)
                            .color(egui::Color32::from_rgb(255, 215, 0)));

                        if self.game.last_match_count >= 4 {
                            ui.add_space(20.0);
                            let bonus_text = if self.game.last_match_count >= 5 {
                                "🔥 MEGA MATCH! +150"
                            } else {
                                "⚡ GREAT MATCH! +50"
                            };
                            ui.label(egui::RichText::new(bonus_text)
                                .size(16.0)
                                .color(egui::Color32::from_rgb(255, 100, 100))
                                .strong());
                        }
                    });
                    ui.add_space(15.0);

                    let board_size = BOARD_SIZE as f32 * CELL_SIZE;
                    let (response, painter) = ui.allocate_painter(
                        egui::vec2(board_size + 20.0, board_size + 20.0),
                        egui::Sense::click(),
                    );

                    let board_min = response.rect.min;

                    painter.rect_filled(
                        egui::Rect::from_min_size(
                            board_min,
                            egui::vec2(board_size + 20.0, board_size + 20.0),
                        ),
                        10.0,
                        egui::Color32::from_rgb(50, 50, 70),
                    );

                    for y in 0..BOARD_SIZE {
                        for x in 0..BOARD_SIZE {
                            let cell_x = board_min.x + 10.0 + x as f32 * CELL_SIZE;
                            let cell_y = board_min.y + 10.0 + y as f32 * CELL_SIZE;
                            let offset = self.game.board[y][x].anim_offset;
                            let draw_y = cell_y - offset;

                            let is_selected = self.game.selected_pos == Some((x, y));
                            let is_hint = self.show_hint && self.is_hint_pos(x, y);

                            let bg_color = if is_selected {
                                egui::Color32::from_rgb(100, 200, 255)
                            } else if is_hint {
                                egui::Color32::from_rgb(255, 255, 150)
                            } else if (x + y) % 2 == 0 {
                                egui::Color32::from_rgb(70, 70, 90)
                            } else {
                                egui::Color32::from_rgb(60, 60, 80)
                            };

                            painter.rect_filled(
                                egui::Rect::from_min_size(
                                    egui::pos2(cell_x + 2.0, draw_y + 2.0),
                                    egui::vec2(CELL_SIZE - 4.0, CELL_SIZE - 4.0),
                                ),
                                8.0,
                                bg_color,
                            );

                            if self.game.board[y][x].emoji != EMPTY {
                                let emoji = EMOJIS[self.game.board[y][x].emoji];
                                painter.text(
                                    egui::pos2(cell_x + CELL_SIZE / 2.0, draw_y + CELL_SIZE / 2.0),
                                    egui::Align2::CENTER_CENTER,
                                    emoji,
                                    egui::FontId::proportional(36.0),
                                    egui::Color32::WHITE,
                                );
                            }
                        }
                    }

                    for p in &self.game.particles {
                        let alpha = (p.life * 255.0) as u8;
                        let size = 6.0 * p.life;
                        painter.circle_filled(
                            egui::pos2(board_min.x + 10.0 + p.x, board_min.y + 10.0 + p.y),
                            size,
                            p.color.gamma_multiply(alpha as f32 / 255.0),
                        );
                    }

                    if response.clicked() {
                        if let Some(pos) = response.interact_pointer_pos() {
                            let rel_x = pos.x - board_min.x - 10.0;
                            let rel_y = pos.y - board_min.y - 10.0;
                            let gx = (rel_x / CELL_SIZE) as usize;
                            let gy = (rel_y / CELL_SIZE) as usize;

                            if gx < BOARD_SIZE && gy < BOARD_SIZE {
                                match self.game.selected_pos {
                                    None => {
                                        self.game.selected_pos = Some((gx, gy));
                                    }
                                    Some(selected) => {
                                        if selected == (gx, gy) {
                                            self.game.selected_pos = None;
                                        } else {
                                            self.game.swap(selected, (gx, gy));
                                            self.show_hint = false;
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ui.add_space(15.0);

                    ui.horizontal(|ui| {
                        if ui.button(egui::RichText::new("🔄 New Game").size(16.0)).clicked() {
                            self.game = Match3Game::new();
                            self.show_hint = false;
                        }
                        ui.add_space(10.0);
                        if ui.button(egui::RichText::new("💡 Hint").size(16.0)).clicked() {
                            self.show_hint = !self.show_hint;
                        }
                        ui.add_space(10.0);
                        if ui.button(egui::RichText::new("↩️ Undo").size(16.0)).clicked() {
                            // Could implement undo stack here
                        }
                    });

                    ui.add_space(10.0);
                    ui.label(egui::RichText::new("Click a piece, then click an adjacent piece to swap!")
                        .size(14.0)
                        .color(egui::Color32::from_rgb(180, 180, 200)));

                    if !self.game.animating && !self.game.has_valid_moves() {
                        ui.add_space(20.0);
                        ui.label(egui::RichText::new("🎉 No more moves! Game Over! 🎉")
                            .size(24.0)
                            .color(egui::Color32::from_rgb(255, 100, 100))
                            .strong());
                        ui.label(egui::RichText::new(format!("Final Score: {}", self.game.score))
                            .size(18.0)
                            .color(egui::Color32::WHITE));
                    }
                });
            });
    }
}

impl Match3App {
    fn is_hint_pos(&self, x: usize, y: usize) -> bool {
        for dy in 0..BOARD_SIZE {
            for dx in 0..BOARD_SIZE {
                if dx + 1 < BOARD_SIZE {
                    let mut temp = self.game.clone();
                    let e1 = temp.board[dy][dx].emoji;
                    let e2 = temp.board[dy][dx+1].emoji;
                    temp.board[dy][dx].emoji = e2;
                    temp.board[dy][dx+1].emoji = e1;
                    if !temp.find_matches().is_empty() {
                        return (x == dx && y == dy) || (x == dx + 1 && y == dy);
                    }
                }
                if dy + 1 < BOARD_SIZE {
                    let mut temp = self.game.clone();
                    let e1 = temp.board[dy][dx].emoji;
                    let e2 = temp.board[dy+1][dx].emoji;
                    temp.board[dy][dx].emoji = e2;
                    temp.board[dy+1][dx].emoji = e1;
                    if !temp.find_matches().is_empty() {
                        return (x == dx && y == dy) || (x == dx && y == dy + 1);
                    }
                }
            }
        }
        false
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([600.0, 700.0])
            .with_resizable(false),
        ..Default::default()
    };

    eframe::run_native(
        "Match-3 Emoji Game",
        options,
        Box::new(|_cc| Ok(Box::new(Match3App::default()))),
    )
}
