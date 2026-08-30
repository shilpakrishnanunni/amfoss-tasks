package main

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

type Process struct {
	ID        string
	Arrival   int
	Burst     int
	Remaining int
}

type Segment struct {
	ID    string
	Start int
	End   int
}

type Result struct {
	ID         string
	Arrival    int
	Burst      int
	Completion int
	Turnaround int
	Waiting    int
}

func main() {
	reader := bufio.NewReader(os.Stdin)

	fmt.Println("=== Grand Line CPU Scheduling Simulator ===")
	fmt.Println("Each pirate crew is a process waiting for CPU execution.")
	fmt.Println()
	fmt.Println("Choose a scheduling algorithm:")
	fmt.Println("1. First Come First Serve (FCFS)")
	fmt.Println("2. Shortest Job First (SJF - Non-Preemptive)")
	fmt.Println("3. Round Robin (RR)")
	fmt.Print("Selection: ")

	choice := readInt(reader, 1, 3)

	fmt.Print("Number of crews: ")
	n := readInt(reader, 1, 1000)

	processes := make([]Process, 0, n)
	seen := make(map[string]bool)

	for i := 0; i < n; i++ {
		fmt.Printf("\nCrew %d\n", i+1)
		fmt.Print("Process ID: ")
		id := readNonEmpty(reader)
		for seen[id] {
			fmt.Print("Process ID already exists. Enter another ID: ")
			id = readNonEmpty(reader)
		}
		seen[id] = true

		fmt.Print("Arrival Time: ")
		arrival := readInt(reader, 0, 1_000_000)

		fmt.Print("Burst Time: ")
		burst := readInt(reader, 1, 1_000_000)

		processes = append(processes, Process{
			ID:        id,
			Arrival:   arrival,
			Burst:     burst,
			Remaining: burst,
		})
	}

	quantum := 0
	if choice == 3 {
		fmt.Print("\nTime Quantum: ")
		quantum = readInt(reader, 1, 1_000_000)
	}

	var segments []Segment
	var results []Result
	var algorithm string

	switch choice {
	case 1:
		algorithm = "First Come First Serve (FCFS)"
		segments, results = fcfs(processes)
	case 2:
		algorithm = "Shortest Job First (SJF - Non-Preemptive)"
		segments, results = sjf(processes)
	case 3:
		algorithm = fmt.Sprintf("Round Robin (RR), Quantum = %d", quantum)
		segments, results = roundRobin(processes, quantum)
	}

	printReport(algorithm, segments, results)
}

func fcfs(processes []Process) ([]Segment, []Result) {
	ps := cloneProcesses(processes)
	sort.SliceStable(ps, func(i, j int) bool {
		if ps[i].Arrival == ps[j].Arrival {
			return i < j
		}
		return ps[i].Arrival < ps[j].Arrival
	})

	var segments []Segment
	results := make([]Result, 0, len(ps))
	time := 0

	for _, p := range ps {
		if time < p.Arrival {
			segments = appendSegment(segments, "IDLE", time, p.Arrival)
			time = p.Arrival
		}
		start := time
		time += p.Burst
		segments = appendSegment(segments, p.ID, start, time)
		results = append(results, makeResult(p, time))
	}

	return segments, results
}

func sjf(processes []Process) ([]Segment, []Result) {
	ps := cloneProcesses(processes)
	done := make([]bool, len(ps))
	results := make([]Result, 0, len(ps))
	var segments []Segment
	time := 0
	completed := 0

	for completed < len(ps) {
		best := -1

		for i, p := range ps {
			if done[i] || p.Arrival > time {
				continue
			}
			if best == -1 ||
				p.Burst < ps[best].Burst ||
				(p.Burst == ps[best].Burst && p.Arrival < ps[best].Arrival) {
				best = i
			}
		}

		if best == -1 {
			next := -1
			for i, p := range ps {
				if !done[i] && (next == -1 || p.Arrival < ps[next].Arrival) {
					next = i
				}
			}
			segments = appendSegment(segments, "IDLE", time, ps[next].Arrival)
			time = ps[next].Arrival
			continue
		}

		p := ps[best]
		start := time
		time += p.Burst
		segments = appendSegment(segments, p.ID, start, time)
		results = append(results, makeResult(p, time))
		done[best] = true
		completed++
	}

	return segments, results
}

func roundRobin(processes []Process, quantum int) ([]Segment, []Result) {
	ps := cloneProcesses(processes)
	sort.SliceStable(ps, func(i, j int) bool {
		if ps[i].Arrival == ps[j].Arrival {
			return i < j
		}
		return ps[i].Arrival < ps[j].Arrival
	})

	type queueItem struct{ index int }
	queue := make([]queueItem, 0, len(ps))
	completion := make([]int, len(ps))
	enqueued := make([]bool, len(ps))
	var segments []Segment

	time := 0
	next := 0
	completed := 0

	enqueueArrivals := func() {
		for next < len(ps) && ps[next].Arrival <= time {
			if !enqueued[next] {
				queue = append(queue, queueItem{next})
				enqueued[next] = true
			}
			next++
		}
	}

	for completed < len(ps) {
		if len(queue) == 0 {
			if next < len(ps) && time < ps[next].Arrival {
				segments = appendSegment(segments, "IDLE", time, ps[next].Arrival)
				time = ps[next].Arrival
			}
			enqueueArrivals()
		}

		if len(queue) == 0 {
			continue
		}

		item := queue[0]
		queue = queue[1:]
		i := item.index

		run := quantum
		if ps[i].Remaining < run {
			run = ps[i].Remaining
		}

		start := time
		time += run
		ps[i].Remaining -= run
		segments = appendSegment(segments, ps[i].ID, start, time)

		enqueueArrivals()

		if ps[i].Remaining > 0 {
			queue = append(queue, queueItem{i})
		} else {
			completion[i] = time
			completed++
		}
	}

	results := make([]Result, 0, len(ps))
	for i, p := range ps {
		results = append(results, makeResult(p, completion[i]))
	}

	return segments, results
}

func makeResult(p Process, completion int) Result {
	turnaround := completion - p.Arrival
	waiting := turnaround - p.Burst
	return Result{
		ID:         p.ID,
		Arrival:    p.Arrival,
		Burst:      p.Burst,
		Completion: completion,
		Turnaround: turnaround,
		Waiting:    waiting,
	}
}

func printReport(algorithm string, segments []Segment, results []Result) {
	fmt.Println("\n=== Simulation Results ===")
	fmt.Println("Algorithm:", algorithm)
	fmt.Println()

	fmt.Println("Gantt Chart / Timeline:")
	fmt.Println(buildTimeline(segments))
	fmt.Println(buildTimeLabels(segments))

	fmt.Println("\nProcess Metrics:")
	fmt.Printf("%-10s %-10s %-10s %-12s %-12s %-10s\n",
		"Process", "Arrival", "Burst", "Completion", "Turnaround", "Waiting")
	fmt.Println(strings.Repeat("-", 68))

	totalWaiting := 0
	totalTurnaround := 0
	for _, r := range results {
		fmt.Printf("%-10s %-10d %-10d %-12d %-12d %-10d\n",
			r.ID, r.Arrival, r.Burst, r.Completion, r.Turnaround, r.Waiting)
		totalWaiting += r.Waiting
		totalTurnaround += r.Turnaround
	}

	n := float64(len(results))
	fmt.Println(strings.Repeat("-", 68))
	fmt.Printf("Average Waiting Time:    %.2f\n", float64(totalWaiting)/n)
	fmt.Printf("Average Turnaround Time: %.2f\n", float64(totalTurnaround)/n)
}

func buildTimeline(segments []Segment) string {
	if len(segments) == 0 {
		return "(no execution)"
	}

	var b strings.Builder
	for _, s := range segments {
		width := s.End - s.Start
		if width < 1 {
			width = 1
		}
		label := fmt.Sprintf(" %s ", s.ID)
		cell := strings.Repeat("-", width*2+1)
		if len(label) > len(cell)-2 {
			label = label[:len(cell)-2]
		}
		left := (len(cell) - len(label)) / 2
		right := len(cell) - len(label) - left
		b.WriteString("|")
		b.WriteString(strings.Repeat("-", left))
		b.WriteString(label)
		b.WriteString(strings.Repeat("-", right))
	}
	b.WriteString("|")
	return b.String()
}

func buildTimeLabels(segments []Segment) string {
	if len(segments) == 0 {
		return ""
	}

	var b strings.Builder
	for i, s := range segments {
		if i == 0 {
			b.WriteString(fmt.Sprintf("%d", s.Start))
		}
		b.WriteString(fmt.Sprintf("%*d", max(3, (s.End-s.Start)*2+1), s.End))
	}
	return b.String()
}

func appendSegment(segments []Segment, id string, start, end int) []Segment {
	if start == end {
		return segments
	}
	if len(segments) > 0 && segments[len(segments)-1].ID == id &&
		segments[len(segments)-1].End == start {
		segments[len(segments)-1].End = end
		return segments
	}
	return append(segments, Segment{ID: id, Start: start, End: end})
}

func cloneProcesses(processes []Process) []Process {
	out := make([]Process, len(processes))
	copy(out, processes)
	for i := range out {
		out[i].Remaining = out[i].Burst
	}
	return out
}

func readInt(reader *bufio.Reader, min, max int) int {
	for {
		text := readNonEmpty(reader)
		value, err := strconv.Atoi(text)
		if err == nil && value >= min && value <= max {
			return value
		}
		fmt.Printf("Enter an integer from %d to %d: ", min, max)
	}
}

func readNonEmpty(reader *bufio.Reader) string {
	for {
		text, err := reader.ReadString('\n')
		if err != nil && len(text) == 0 {
			os.Exit(0)
		}
		text = strings.TrimSpace(text)
		if text != "" {
			return text
		}
		fmt.Print("Input cannot be empty. Try again: ")
	}
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
