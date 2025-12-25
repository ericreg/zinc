struct BankAccount {
    _account_number: i32,
    _balance: i32,
    pub owner: String,
    pub bank_name: String,
}

impl BankAccount {
    fn new(owner: String, account_number: i32, initial_balance: i32) -> Self {
        return BankAccount { _account_number: account_number, _balance: initial_balance, owner: owner, bank_name: String::from("Zinc Bank") };
    }
    fn get_balance(&self) -> i32 {
        return self._balance;
    }
    fn deposit(&mut self, amount: i32) {
        self._balance = (self._balance + amount);
    }
    fn withdraw(&mut self, amount: i32) {
        self._balance = (self._balance - amount);
    }
    fn summary(&self) -> String {
        return format!("Account for {} at {}", self.owner, self.bank_name);
    }
    fn transfer_fee() -> i64 {
        return 5;
    }
}

struct Transaction {
    pub from_account: String,
    pub to_account: String,
    pub amount: i32,
    _processed: bool,
}

impl Transaction {
    fn new(from: String, to: String, amount: i32) -> Self {
        return Transaction { from_account: from, to_account: to, amount: amount, _processed: false };
    }
    fn mark_processed(&mut self) {
        self._processed = true;
    }
    fn is_processed(&self) -> bool {
        return self._processed;
    }
    fn describe(&self) -> String {
        return format!("Transfer {} from {} to {}", self.amount, self.from_account, self.to_account);
    }
}

fn main() {
    let mut alice_account = BankAccount::new(String::from("Alice"), (1001) as i32, (1000) as i32);
    let mut bob_account = BankAccount::new(String::from("Bob"), (1002) as i32, (500) as i32);
    println!("{}", alice_account.summary());
    println!("{}", bob_account.summary());
    println!("{}", alice_account.get_balance());
    println!("{}", bob_account.get_balance());
    alice_account.deposit((200) as i32);
    println!("{}", alice_account.get_balance());
    let mut tx = Transaction::new(String::from("Alice"), String::from("Bob"), (100) as i32);
    println!("{}", tx.describe());
    let fee = BankAccount::transfer_fee();
    alice_account.withdraw(((100 + fee)) as i32);
    bob_account.deposit((100) as i32);
    tx.mark_processed();
    println!("{}", alice_account.get_balance());
    println!("{}", bob_account.get_balance());
}