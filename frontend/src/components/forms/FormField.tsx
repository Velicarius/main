import { forwardRef } from 'react';
import { Input, InputProps } from '../ui/Input';
import { FieldError } from 'react-hook-form';

export interface FormFieldProps extends Omit<InputProps, 'error'> {
  name: string;
  label?: string;
  error?: FieldError | string;
  helpText?: string;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ name, label, error, helpText, ...inputProps }, ref) => {
    const errorMessage = typeof error === 'string' ? error : error?.message;

    return (
      <div className="w-full">
        <Input
          ref={ref}
          id={name}
          label={label}
          error={errorMessage}
          {...inputProps}
        />
        {helpText && !errorMessage && (
          <p className="mt-2 text-xs text-slate-500">
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

FormField.displayName = 'FormField';
