#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_active_bool_author_String {
    active: bool,
    author: String,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_likes_i64_views_i64 {
    likes: i64,
    views: i64,
}

#[derive(Clone, Default)]
struct __ZincAnonStruct_AnonStruct_meta_AnonStruct_active_bool_author_String_stats_AnonStruct_likes_i64_views_i64 {
    meta: __ZincAnonStruct_AnonStruct_active_bool_author_String,
    stats: __ZincAnonStruct_AnonStruct_likes_i64_views_i64,
}

fn main() {
    let post = __ZincAnonStruct_AnonStruct_meta_AnonStruct_active_bool_author_String_stats_AnonStruct_likes_i64_views_i64 { meta: __ZincAnonStruct_AnonStruct_active_bool_author_String { author: String::from("alice"), active: true }, stats: __ZincAnonStruct_AnonStruct_likes_i64_views_i64 { views: 10, likes: 2 } };
    println!("{}", post.meta.author);
    println!("{}", post.meta.active);
    println!("{}", post.stats.views);
    println!("{}", post.stats.likes);
}