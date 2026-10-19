import Button from '../common/Button';
import Input from '../common/Input';

type SearchBarProps = {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
};

export default function SearchBar({ value, onChange, onSearch }: SearchBarProps) {
  return (
    <form
      className="flex flex-col gap-3 sm:flex-row"
      onSubmit={(event) => {
        event.preventDefault();
        onSearch();
      }}
    >
      <div className="flex-1">
        <Input
          id="memory-search"
          value={value}
          onChange={onChange}
          placeholder="Describe the Reel or Short you're trying to find..."
        />
      </div>
      <Button type="submit" className="min-h-12 px-7">Search videos</Button>
    </form>
  );
}
