use std::fs;
use std::path::Path;
use std::process::Command;

fn main() {
    let tests = [
        "basic_dynamic_type",
        "arithmetic",
        "if_else",
        "reassign_type",
        "variable_assignment",
        "functions",
        "spawn",
    ];

    let output_dir = Path::new("../output");
    fs::create_dir_all(output_dir).expect("Failed to create output directory");

    for test_name in tests {
        println!("Running {}...", test_name);

        let result = Command::new("cargo")
            .args(["run", "--bin", test_name, "-q"])
            .output()
            .expect("Failed to execute command");

        let output = String::from_utf8_lossy(&result.stdout);

        let output_file = output_dir.join(format!("{}.out", test_name));
        fs::write(&output_file, output.as_bytes())
            .expect(&format!("Failed to write {}", output_file.display()));

        if result.status.success() {
            println!("  OK -> {}", output_file.display());
        } else {
            let stderr = String::from_utf8_lossy(&result.stderr);
            println!("  FAILED: {}", stderr);
        }
    }

    println!("\nDone! Output files written to {:?}", output_dir);
}
