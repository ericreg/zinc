struct operators_03_overloading__Bag {
    pub value: i64,
}

impl Default for operators_03_overloading__Bag {
    fn default() -> Self {
        Self { value: 0 }
    }
}

impl operators_03_overloading__Bag {
    fn __zinc_op_in(&self, candidate: i64) -> bool {
        return (candidate == self.value);
    }
}

struct operators_03_overloading__Offset {
    pub value: i64,
}

impl Default for operators_03_overloading__Offset {
    fn default() -> Self {
        Self { value: 0 }
    }
}

impl operators_03_overloading__Offset {
    fn __zinc_op_add(left: Self, amount: i64) -> Self {
        return operators_03_overloading__Offset { value: (left.value + amount) };
    }
    fn __zinc_op_sub(&self) -> Self {
        return operators_03_overloading__Offset { value: (0 - self.value) };
    }
    fn __zinc_op_range(left: Self, right: Self) -> Self {
        return operators_03_overloading__Offset { value: (right.value - left.value) };
    }
}

struct operators_03_overloading__Point {
    pub x: i64,
    pub y: i64,
}

impl Default for operators_03_overloading__Point {
    fn default() -> Self {
        Self { x: 0, y: 0 }
    }
}

impl operators_03_overloading__Point {
    fn __zinc_op_eq(left: Self, right: Self) -> bool {
        return ((left.x == right.x) && (left.y == right.y));
    }
    fn __zinc_op_add(&self, rhs: Self) -> Self {
        return operators_03_overloading__Point { x: (self.x + rhs.x), y: (self.y + rhs.y) };
    }
    fn __zinc_op_index(&self, idx: i64) -> i64 {
        if (idx == 0) {
            return self.x;
        }
        return self.y;
    }
    fn __zinc_op_custom_24_24(left: Self, right: Self) -> Self {
        return operators_03_overloading__Point { x: (left.x + right.y), y: (left.y + right.x) };
    }
}

fn main() {
    let a = operators_03_overloading__Point { x: 1, y: 2 };
    let b = operators_03_overloading__Point { x: 3, y: 4 };
    let c = (a).__zinc_op_add(b);
    println!("{}", c.x);
    let mut d = operators_03_overloading__Point { x: 5, y: 6 };
    let e = operators_03_overloading__Point { x: 7, y: 8 };
    d = (d).__zinc_op_add(e);
    println!("{}", d.y);
    let f = operators_03_overloading__Point { x: 1, y: 2 };
    println!("{}", (f).__zinc_op_index(0));
    let g = operators_03_overloading__Point { x: 1, y: 2 };
    let h = operators_03_overloading__Point { x: 1, y: 9 };
    let i = operators_03_overloading__Point::__zinc_op_custom_24_24(g, h);
    println!("{}", i.x);
    let j = operators_03_overloading__Point { x: 1, y: 2 };
    let k = operators_03_overloading__Point { x: 1, y: 2 };
    println!("{}", operators_03_overloading__Point::__zinc_op_eq(j, k));
    let o = operators_03_overloading__Offset { value: 10 };
    let p = operators_03_overloading__Offset::__zinc_op_add(o, 5);
    println!("{}", p.value);
    let q = (p).__zinc_op_sub();
    println!("{}", q.value);
    let r = operators_03_overloading__Offset { value: 2 };
    let s = operators_03_overloading__Offset { value: 9 };
    let span = operators_03_overloading__Offset::__zinc_op_range(r, s);
    println!("{}", span.value);
    let bag = operators_03_overloading__Bag { value: 42 };
    println!("{}", (bag).__zinc_op_in(42));
}